"""Tests for Recurring CRUD."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def setup(client: AsyncClient):
    acc = (await client.post("/api/accounts", json={
        "name": "Main", "type": "bank", "balance": 10000
    })).json()
    cat = (await client.post("/api/categories", json={
        "name": "Bills", "type": "expense"
    })).json()
    return {"account_id": acc["id"], "category_id": cat["id"]}


async def test_create_recurring(client: AsyncClient, setup):
    r = await client.post("/api/recurring", json={
        "type": "expense", "amount": 500, "accountId": setup["account_id"],
        "categoryId": setup["category_id"], "description": "Internet",
        "frequency": "monthly", "startDate": "2026-04-01", "nextRunDate": "2026-05-01"
    })
    assert r.status_code == 201
    data = r.json()
    assert data["description"] == "Internet"
    assert data["frequency"] == "monthly"


async def test_list_recurring(client: AsyncClient, setup):
    await client.post("/api/recurring", json={
        "type": "expense", "amount": 200, "accountId": setup["account_id"],
        "description": "Phone", "frequency": "monthly",
        "startDate": "2026-04-01", "nextRunDate": "2026-05-01"
    })
    r = await client.get("/api/recurring")
    assert r.status_code == 200
    assert len(r.json()) >= 1


async def test_update_recurring(client: AsyncClient, setup):
    created = (await client.post("/api/recurring", json={
        "type": "expense", "amount": 200, "accountId": setup["account_id"],
        "description": "Phone", "frequency": "monthly",
        "startDate": "2026-04-01", "nextRunDate": "2026-05-01"
    })).json()
    r = await client.put(f"/api/recurring/{created['id']}", json={"amount": 300})
    assert r.status_code == 200
    assert r.json()["amount"] == 300


async def test_patch_recurring(client: AsyncClient, setup):
    created = (await client.post("/api/recurring", json={
        "type": "expense", "amount": 200, "accountId": setup["account_id"],
        "description": "Phone", "frequency": "monthly",
        "startDate": "2026-04-01", "nextRunDate": "2026-05-01"
    })).json()
    r = await client.patch(f"/api/recurring/{created['id']}", json={"isActive": False})
    assert r.status_code == 200
    assert r.json()["isActive"] is False


async def test_delete_recurring(client: AsyncClient, setup):
    created = (await client.post("/api/recurring", json={
        "type": "expense", "amount": 200, "accountId": setup["account_id"],
        "description": "Phone", "frequency": "monthly",
        "startDate": "2026-04-01", "nextRunDate": "2026-05-01"
    })).json()
    r = await client.delete(f"/api/recurring/{created['id']}")
    assert r.status_code == 200
    assert r.json()["success"] is True
