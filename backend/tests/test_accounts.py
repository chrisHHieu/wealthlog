"""Tests for Accounts CRUD + balance logic."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def account_data():
    return {"name": "Test Cash", "type": "cash", "balance": 1000, "currency": "VND"}


async def test_create_account(client: AsyncClient, account_data):
    r = await client.post("/api/accounts", json=account_data)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Test Cash"
    assert data["type"] == "cash"
    assert data["balance"] == 1000
    assert "id" in data


async def test_list_accounts(client: AsyncClient, account_data):
    await client.post("/api/accounts", json=account_data)
    r = await client.get("/api/accounts")
    assert r.status_code == 200
    assert len(r.json()) >= 1


async def test_get_account(client: AsyncClient, account_data):
    created = (await client.post("/api/accounts", json=account_data)).json()
    r = await client.get(f"/api/accounts/{created['id']}")
    assert r.status_code == 200
    assert r.json()["name"] == "Test Cash"


async def test_get_account_not_found(client: AsyncClient):
    r = await client.get("/api/accounts/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


async def test_update_account(client: AsyncClient, account_data):
    created = (await client.post("/api/accounts", json=account_data)).json()
    r = await client.put(f"/api/accounts/{created['id']}", json={"name": "Updated"})
    assert r.status_code == 200
    assert r.json()["name"] == "Updated"


async def test_delete_account(client: AsyncClient, account_data):
    created = (await client.post("/api/accounts", json=account_data)).json()
    r = await client.delete(f"/api/accounts/{created['id']}")
    assert r.status_code == 200
    assert r.json()["success"] is True

    r2 = await client.get(f"/api/accounts/{created['id']}")
    assert r2.status_code == 404
