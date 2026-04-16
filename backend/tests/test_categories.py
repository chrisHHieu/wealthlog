"""Tests for Categories CRUD."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def category_data():
    return {"name": "Test Food", "type": "expense", "icon": "🍜", "color": "#f59e0b"}


async def test_create_category(client: AsyncClient, category_data):
    r = await client.post("/api/categories", json=category_data)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Test Food"
    assert data["type"] == "expense"


async def test_list_categories(client: AsyncClient, category_data):
    await client.post("/api/categories", json=category_data)
    r = await client.get("/api/categories")
    assert r.status_code == 200
    assert len(r.json()) >= 1


async def test_update_category(client: AsyncClient, category_data):
    created = (await client.post("/api/categories", json=category_data)).json()
    r = await client.put(f"/api/categories?id={created['id']}", json={"name": "Updated Food"})
    assert r.status_code == 200
    assert r.json()["name"] == "Updated Food"


async def test_delete_category(client: AsyncClient, category_data):
    created = (await client.post("/api/categories", json=category_data)).json()
    r = await client.delete(f"/api/categories?id={created['id']}")
    assert r.status_code == 200
    assert r.json()["success"] is True


async def test_used_only_filter(client: AsyncClient):
    # Create category + account + transaction to make category "used"
    cat = (await client.post("/api/categories", json={
        "name": "Used Cat", "type": "expense"
    })).json()
    acc = (await client.post("/api/accounts", json={
        "name": "Acc", "type": "cash", "balance": 5000
    })).json()
    await client.post("/api/transactions", json={
        "type": "expense", "amount": 100, "accountId": acc["id"],
        "categoryId": cat["id"], "date": "2026-04-15", "description": "test"
    })

    r = await client.get("/api/categories?usedOnly=true&startDate=2026-04-01&endDate=2026-04-30")
    assert r.status_code == 200
    names = [c["name"] for c in r.json()]
    assert "Used Cat" in names
