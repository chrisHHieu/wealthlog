"""Tests for Transactions CRUD + balance sync."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def setup(client: AsyncClient):
    """Create account + category for transaction tests."""
    acc = (await client.post("/api/accounts", json={
        "name": "Main", "type": "bank", "balance": 10000
    })).json()
    cat = (await client.post("/api/categories", json={
        "name": "Food", "type": "expense"
    })).json()
    return {"account_id": acc["id"], "category_id": cat["id"]}


async def test_create_income(client: AsyncClient, setup):
    r = await client.post("/api/transactions", json={
        "type": "income", "amount": 500, "accountId": setup["account_id"],
        "categoryId": setup["category_id"], "date": "2026-04-15", "description": "salary"
    })
    assert r.status_code == 201
    # Balance should increase
    acc = (await client.get(f"/api/accounts/{setup['account_id']}")).json()
    assert acc["balance"] == 10500


async def test_create_expense(client: AsyncClient, setup):
    r = await client.post("/api/transactions", json={
        "type": "expense", "amount": 300, "accountId": setup["account_id"],
        "categoryId": setup["category_id"], "date": "2026-04-15", "description": "lunch"
    })
    assert r.status_code == 201
    acc = (await client.get(f"/api/accounts/{setup['account_id']}")).json()
    assert acc["balance"] == 9700


async def test_create_transfer(client: AsyncClient, setup):
    acc2 = (await client.post("/api/accounts", json={
        "name": "Savings", "type": "savings", "balance": 0
    })).json()
    r = await client.post("/api/transactions", json={
        "type": "transfer", "amount": 2000, "accountId": setup["account_id"],
        "toAccountId": acc2["id"], "date": "2026-04-15", "description": "save"
    })
    assert r.status_code == 201
    src = (await client.get(f"/api/accounts/{setup['account_id']}")).json()
    dst = (await client.get(f"/api/accounts/{acc2['id']}")).json()
    assert src["balance"] == 8000
    assert dst["balance"] == 2000


async def test_create_transfer_requires_destination(client: AsyncClient, setup):
    r = await client.post("/api/transactions", json={
        "type": "transfer", "amount": 2000, "accountId": setup["account_id"],
        "date": "2026-04-15", "description": "save"
    })
    assert r.status_code == 422

    acc = (await client.get(f"/api/accounts/{setup['account_id']}")).json()
    assert acc["balance"] == 10000


async def test_create_income_rejects_destination(client: AsyncClient, setup):
    acc2 = (await client.post("/api/accounts", json={
        "name": "Savings", "type": "savings", "balance": 0
    })).json()
    r = await client.post("/api/transactions", json={
        "type": "income", "amount": 500, "accountId": setup["account_id"],
        "toAccountId": acc2["id"], "date": "2026-04-15", "description": "salary"
    })
    assert r.status_code == 422

    src = (await client.get(f"/api/accounts/{setup['account_id']}")).json()
    dst = (await client.get(f"/api/accounts/{acc2['id']}")).json()
    assert src["balance"] == 10000
    assert dst["balance"] == 0


async def test_list_transactions(client: AsyncClient, setup):
    await client.post("/api/transactions", json={
        "type": "expense", "amount": 100, "accountId": setup["account_id"],
        "date": "2026-04-15", "description": "test"
    })
    r = await client.get("/api/transactions")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


async def test_list_transactions_paginated(client: AsyncClient, setup):
    await client.post("/api/transactions", json={
        "type": "expense", "amount": 100, "accountId": setup["account_id"],
        "date": "2026-04-15", "description": "test"
    })
    r = await client.get("/api/transactions?page=1&pageSize=10")
    assert r.status_code == 200
    data = r.json()
    assert "data" in data
    assert "total" in data
    assert "totalPages" in data


async def test_update_transaction_reverses_balance(client: AsyncClient, setup):
    tx = (await client.post("/api/transactions", json={
        "type": "expense", "amount": 200, "accountId": setup["account_id"],
        "date": "2026-04-15", "description": "old"
    })).json()
    # Balance: 10000 - 200 = 9800
    acc = (await client.get(f"/api/accounts/{setup['account_id']}")).json()
    assert acc["balance"] == 9800

    await client.put(f"/api/transactions/{tx['id']}", json={"amount": 500})
    # Reverse: +200, Apply: -500 → 9800 + 200 - 500 = 9500
    acc = (await client.get(f"/api/accounts/{setup['account_id']}")).json()
    assert acc["balance"] == 9500


async def test_delete_transaction_reverses_balance(client: AsyncClient, setup):
    tx = (await client.post("/api/transactions", json={
        "type": "expense", "amount": 300, "accountId": setup["account_id"],
        "date": "2026-04-15", "description": "to delete"
    })).json()
    acc = (await client.get(f"/api/accounts/{setup['account_id']}")).json()
    assert acc["balance"] == 9700

    await client.delete(f"/api/transactions/{tx['id']}")
    acc = (await client.get(f"/api/accounts/{setup['account_id']}")).json()
    assert acc["balance"] == 10000


async def test_filter_by_type(client: AsyncClient, setup):
    await client.post("/api/transactions", json={
        "type": "income", "amount": 100, "accountId": setup["account_id"],
        "date": "2026-04-15", "description": "inc"
    })
    await client.post("/api/transactions", json={
        "type": "expense", "amount": 50, "accountId": setup["account_id"],
        "date": "2026-04-15", "description": "exp"
    })
    r = await client.get("/api/transactions?type=income")
    data = r.json()
    assert all(t["type"] == "income" for t in data)
