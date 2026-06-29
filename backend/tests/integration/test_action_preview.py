"""Confirmation-card previews: deferred writes resolve to human-readable effects."""

from contextlib import asynccontextmanager
from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent.action_preview import build_action_preview


def _patch_session(db: AsyncSession):
    @asynccontextmanager
    async def _m():
        yield db

    return patch("app.ai.agent.action_preview.get_session", _m)


async def _seed(client: AsyncClient) -> dict:
    acc = (await client.post("/api/accounts", json={
        "name": "Main", "type": "bank", "balance": 1_000_000,
    })).json()
    cat_old = (await client.post("/api/categories", json={
        "name": "Healthcare", "type": "expense",
    })).json()
    await client.post("/api/categories", json={"name": "Bills & Utilities", "type": "expense"})
    tx = (await client.post("/api/transactions", json={
        "type": "expense", "amount": 350_000, "accountId": acc["id"],
        "categoryId": cat_old["id"], "date": "2026-06-10", "description": "Electricity",
    })).json()
    return {"account": acc, "tx": tx}


async def test_create_preview_describes_new_transaction(db: AsyncSession):
    # create needs no existing row — preview is built from the arguments alone.
    with _patch_session(db):
        preview = await build_action_preview("create_transaction", {
            "type": "expense", "amount": 50_000, "description": "Coffee",
            "category_name": "Food", "account_name": "Main", "date": "2026-06-10",
        })
    assert preview["summary"] == "Create transaction"
    [item] = preview["items"]
    assert "Coffee" in item["label"]
    assert "50,000 VND" in item["label"]
    assert item["detail"] == "expense · Food · Main"


async def test_update_preview_shows_old_to_new_diff(client: AsyncClient, db: AsyncSession):
    seeded = await _seed(client)
    with _patch_session(db):
        preview = await build_action_preview("update_transaction", {
            "transaction_id": seeded["tx"]["id"], "category_name": "Bills & Utilities",
        })
    assert preview["summary"] == "Update transaction"
    [item] = preview["items"]
    assert "Electricity" in item["label"]
    assert "350,000 VND" in item["label"]
    assert item["detail"] == "Healthcare → Bills & Utilities"


async def test_delete_preview_describes_the_row(client: AsyncClient, db: AsyncSession):
    seeded = await _seed(client)
    with _patch_session(db):
        preview = await build_action_preview("delete_transaction", {
            "transaction_id": seeded["tx"]["id"],
        })
    assert preview["summary"] == "Delete transaction"
    assert preview["items"][0]["detail"] == "will be deleted"
    assert "Electricity" in preview["items"][0]["label"]


async def test_update_multiple_preview_folds_common_change_into_summary(
    client: AsyncClient, db: AsyncSession,
):
    acc = (await client.post("/api/accounts", json={
        "name": "Main", "type": "bank", "balance": 1_000_000,
    })).json()
    cat_old = (await client.post("/api/categories", json={
        "name": "Healthcare", "type": "expense",
    })).json()
    await client.post("/api/categories", json={"name": "Bills & Utilities", "type": "expense"})
    ids = []
    for desc in ("Electricity", "Water"):
        tx = (await client.post("/api/transactions", json={
            "type": "expense", "amount": 350_000, "accountId": acc["id"],
            "categoryId": cat_old["id"], "date": "2026-06-10", "description": desc,
        })).json()
        ids.append(tx["id"])

    with _patch_session(db):
        preview = await build_action_preview("update_multiple_transactions", {
            "updates": [
                {"transaction_id": ids[0], "category_name": "Bills & Utilities"},
                {"transaction_id": ids[1], "category_name": "Bills & Utilities"},
            ],
        })
    # All items share the same change → it is folded into the one-line summary.
    assert preview["summary"] == "Update 2 transactions · Healthcare → Bills & Utilities"
    assert len(preview["items"]) == 2


async def test_preview_none_for_missing_transaction(db: AsyncSession):
    with _patch_session(db):
        preview = await build_action_preview("update_transaction", {
            "transaction_id": "not-a-uuid", "category_name": "X",
        })
    assert preview is None
