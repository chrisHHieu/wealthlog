"""Batch write tools: atomic multi-update / multi-delete with balance sync."""

from contextlib import asynccontextmanager
from unittest.mock import patch
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent.tools import execute_tool
from app.models.account import Account
from app.models.transaction import Transaction


def _patch_session(db: AsyncSession):
    @asynccontextmanager
    async def _m():
        yield db

    return patch("app.ai.mcp.tools.transaction_batch.get_session", _m)


async def _seed_two_expenses(client: AsyncClient) -> dict:
    acc = (await client.post("/api/accounts", json={
        "name": "Main", "type": "bank", "balance": 1_000_000,
    })).json()
    cat = (await client.post("/api/categories", json={"name": "Food", "type": "expense"})).json()
    new_cat = (await client.post("/api/categories", json={
        "name": "Dining", "type": "expense",
    })).json()
    ids = []
    for desc in ("Lunch", "Dinner"):
        tx = (await client.post("/api/transactions", json={
            "type": "expense", "amount": 100_000, "accountId": acc["id"],
            "categoryId": cat["id"], "date": "2026-06-10", "description": desc,
        })).json()
        ids.append(tx["id"])
    return {"account_id": acc["id"], "new_cat_id": new_cat["id"], "ids": ids}


async def test_update_multiple_recategorizes_all_atomically(
    client: AsyncClient, db: AsyncSession,
):
    s = await _seed_two_expenses(client)
    with _patch_session(db):
        text, is_error = await execute_tool("update_multiple_transactions", {
            "updates": [
                {"transaction_id": s["ids"][0], "category_name": "Dining"},
                {"transaction_id": s["ids"][1], "category_name": "Dining"},
            ],
        })
    assert is_error is False
    assert "Updated 2 transactions" in text
    for tid in s["ids"]:
        tx = await db.get(Transaction, UUID(tid))
        assert str(tx.category_id) == s["new_cat_id"]


async def test_delete_multiple_restores_balance(client: AsyncClient, db: AsyncSession):
    s = await _seed_two_expenses(client)
    # Two 100k expenses against a 1,000,000 balance → 800,000.
    acc = await db.get(Account, UUID(s["account_id"]))
    assert acc.balance == 800_000

    with _patch_session(db):
        text, is_error = await execute_tool("delete_multiple_transactions", {
            "transaction_ids": s["ids"],
        })
    assert is_error is False
    assert "Deleted 2 transactions" in text
    await db.refresh(acc)
    assert acc.balance == 1_000_000
    for tid in s["ids"]:
        assert await db.get(Transaction, UUID(tid)) is None


async def test_update_multiple_is_atomic_on_bad_id(client: AsyncClient, db: AsyncSession):
    s = await _seed_two_expenses(client)
    with _patch_session(db):
        text, is_error = await execute_tool("update_multiple_transactions", {
            "updates": [
                {"transaction_id": s["ids"][0], "category_name": "Dining"},
                {"transaction_id": "00000000-0000-0000-0000-000000000000",
                 "category_name": "Dining"},
            ],
        })
    # Validation fails before any write — nothing is changed.
    assert is_error is True
    tx = await db.get(Transaction, UUID(s["ids"][0]))
    assert str(tx.category_id) != s["new_cat_id"]


async def test_delete_multiple_empty_list_errors(db: AsyncSession):
    with _patch_session(db):
        _, is_error = await execute_tool("delete_multiple_transactions", {"transaction_ids": []})
    assert is_error is True
