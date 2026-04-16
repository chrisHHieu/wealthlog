"""Tests for Investments CRUD."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def inv_data():
    return {
        "name": "VNM Stock",
        "type": "stock",
        "symbol": "VNM",
        "quantity": 100,
        "buyPrice": 80000,
        "currentPrice": 85000,
        "buyDate": "2026-01-15",
    }


async def test_create_investment(client: AsyncClient, inv_data):
    r = await client.post("/api/investments", json=inv_data)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "VNM Stock"
    assert data["quantity"] == 100


async def test_list_investments(client: AsyncClient, inv_data):
    await client.post("/api/investments", json=inv_data)
    r = await client.get("/api/investments")
    assert r.status_code == 200
    assert len(r.json()) >= 1


async def test_update_investment(client: AsyncClient, inv_data):
    created = (await client.post("/api/investments", json=inv_data)).json()
    r = await client.put(f"/api/investments/{created['id']}", json={"currentPrice": 90000})
    assert r.status_code == 200
    assert r.json()["currentPrice"] == 90000


async def test_delete_investment(client: AsyncClient, inv_data):
    created = (await client.post("/api/investments", json=inv_data)).json()
    r = await client.delete(f"/api/investments/{created['id']}")
    assert r.status_code == 200
    assert r.json()["success"] is True

    r2 = await client.get("/api/investments")
    ids = [i["id"] for i in r2.json()]
    assert created["id"] not in ids
