"""Tests for Goals CRUD + contributions."""

import pytest
from httpx import AsyncClient


@pytest.fixture
async def goal_data():
    return {
        "name": "Emergency Fund",
        "type": "emergency",
        "targetAmount": 10000,
        "currentAmount": 0,
        "deadline": "2026-12-31",
    }


async def test_create_goal(client: AsyncClient, goal_data):
    r = await client.post("/api/goals", json=goal_data)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Emergency Fund"
    assert data["targetAmount"] == 10000
    assert data["isCompleted"] is False


async def test_list_goals(client: AsyncClient, goal_data):
    await client.post("/api/goals", json=goal_data)
    r = await client.get("/api/goals")
    assert r.status_code == 200
    assert len(r.json()) >= 1


async def test_get_goal(client: AsyncClient, goal_data):
    created = (await client.post("/api/goals", json=goal_data)).json()
    r = await client.get(f"/api/goals/{created['id']}")
    assert r.status_code == 200
    assert r.json()["name"] == "Emergency Fund"


async def test_update_goal(client: AsyncClient, goal_data):
    created = (await client.post("/api/goals", json=goal_data)).json()
    r = await client.put(f"/api/goals/{created['id']}", json={"name": "Rainy Day"})
    assert r.status_code == 200
    assert r.json()["name"] == "Rainy Day"


async def test_contribute_to_goal(client: AsyncClient, goal_data):
    created = (await client.post("/api/goals", json=goal_data)).json()
    r = await client.post(f"/api/goals/{created['id']}/contribute", json={
        "amount": 3000, "note": "Monthly savings", "date": "2026-04-15"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["currentAmount"] == 3000
    assert len(data["contributions"]) == 1
    assert data["contributions"][0]["amount"] == 3000


async def test_goal_completes_on_target(client: AsyncClient, goal_data):
    created = (await client.post("/api/goals", json=goal_data)).json()
    await client.post(f"/api/goals/{created['id']}/contribute", json={
        "amount": 10000, "note": "Full fund", "date": "2026-04-15"
    })
    r = await client.get(f"/api/goals/{created['id']}")
    assert r.json()["isCompleted"] is True


async def test_delete_goal(client: AsyncClient, goal_data):
    created = (await client.post("/api/goals", json=goal_data)).json()
    r = await client.delete(f"/api/goals/{created['id']}")
    assert r.status_code == 200
    assert r.json()["success"] is True
