"""Tests for Budgets CRUD + check."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def setup(client: AsyncClient):
    cat = (await client.post("/api/categories", json={
        "name": "Food", "type": "expense", "budgetGroup": "needs"
    })).json()
    acc = (await client.post("/api/accounts", json={
        "name": "Main", "type": "bank", "balance": 50000
    })).json()
    return {"category_id": cat["id"], "account_id": acc["id"]}


async def test_create_budget(client: AsyncClient, setup):
    r = await client.post("/api/budgets", json={
        "categoryId": setup["category_id"], "amount": 5000, "month": "2026-04"
    })
    assert r.status_code == 201
    assert r.json()["amount"] == 5000


async def test_list_budgets(client: AsyncClient, setup):
    await client.post("/api/budgets", json={
        "categoryId": setup["category_id"], "amount": 5000, "month": "2026-04"
    })
    r = await client.get("/api/budgets?month=2026-04")
    assert r.status_code == 200
    assert len(r.json()) >= 1


async def test_delete_budget(client: AsyncClient, setup):
    created = (await client.post("/api/budgets", json={
        "categoryId": setup["category_id"], "amount": 5000, "month": "2026-04"
    })).json()
    r = await client.delete(f"/api/budgets?id={created['id']}")
    assert r.status_code == 200
    assert r.json()["success"] is True


async def test_budget_upsert(client: AsyncClient, setup):
    """Creating budget for same category+month should replace the old one."""
    await client.post("/api/budgets", json={
        "categoryId": setup["category_id"], "amount": 3000, "month": "2026-04"
    })
    await client.post("/api/budgets", json={
        "categoryId": setup["category_id"], "amount": 7000, "month": "2026-04"
    })
    r = await client.get("/api/budgets?month=2026-04")
    budgets = r.json()
    cat_budgets = [b for b in budgets if b["categoryId"] == setup["category_id"]]
    assert len(cat_budgets) == 1
    assert cat_budgets[0]["amount"] == 7000


async def test_budget_check(client: AsyncClient, setup):
    await client.post("/api/budgets", json={
        "categoryId": setup["category_id"], "amount": 5000, "month": "2026-04"
    })
    # Add an expense transaction
    await client.post("/api/transactions", json={
        "type": "expense", "amount": 4500, "accountId": setup["account_id"],
        "categoryId": setup["category_id"], "date": "2026-04-10", "description": "food"
    })
    r = await client.get(f"/api/budgets/check?categoryId={setup['category_id']}&month=2026-04")
    assert r.status_code == 200
    data = r.json()
    assert data["budgetAmount"] == 5000
    assert data["totalSpent"] == 4500
    assert data["percent"] == 90
    assert data["isWarning"] is True
    assert data["isExceeded"] is False


async def test_budget_check_exceeded(client: AsyncClient, setup):
    await client.post("/api/budgets", json={
        "categoryId": setup["category_id"], "amount": 1000, "month": "2026-04"
    })
    await client.post("/api/transactions", json={
        "type": "expense", "amount": 1500, "accountId": setup["account_id"],
        "categoryId": setup["category_id"], "date": "2026-04-10", "description": "food"
    })
    r = await client.get(f"/api/budgets/check?categoryId={setup['category_id']}&month=2026-04")
    data = r.json()
    assert data["isExceeded"] is True


async def test_budget_check_no_budget(client: AsyncClient, setup):
    r = await client.get(f"/api/budgets/check?categoryId={setup['category_id']}&month=2026-04")
    assert r.status_code == 200
    assert r.json() is None
