"""Tests for Dashboard, Reports, and Settings endpoints."""

import pytest
from httpx import AsyncClient


async def test_request_id_header_is_returned(client: AsyncClient):
    r = await client.get("/health", headers={"X-Request-ID": "test-request-id"})
    assert r.status_code == 200
    assert r.headers["X-Request-ID"] == "test-request-id"


@pytest.fixture
async def populated(client: AsyncClient):
    """Create sample data for dashboard/reports tests."""
    acc = (await client.post("/api/accounts", json={
        "name": "Main", "type": "bank", "balance": 50000
    })).json()
    cat = (await client.post("/api/categories", json={
        "name": "Food", "type": "expense", "budgetGroup": "needs"
    })).json()
    inc_cat = (await client.post("/api/categories", json={
        "name": "Salary", "type": "income"
    })).json()

    await client.post("/api/transactions", json={
        "type": "income", "amount": 20000, "accountId": acc["id"],
        "categoryId": inc_cat["id"], "date": "2026-04-05", "description": "salary"
    })
    await client.post("/api/transactions", json={
        "type": "expense", "amount": 5000, "accountId": acc["id"],
        "categoryId": cat["id"], "date": "2026-04-10", "description": "groceries"
    })
    await client.post("/api/budgets", json={
        "categoryId": cat["id"], "amount": 10000, "month": "2026-04"
    })
    return {"account_id": acc["id"], "category_id": cat["id"]}


# ── Dashboard ──────────────────────────────────────────────


async def test_dashboard_returns_all_fields(client: AsyncClient, populated):
    r = await client.get("/api/dashboard?month=2026-04")
    assert r.status_code == 200
    data = r.json()
    assert "netWorth" in data
    assert "selectedMonth" in data
    assert "currentMonth" in data
    assert "previousMonth" in data
    assert "monthlyChart" in data
    assert "categoryBreakdown" in data
    assert "spendingByGroup" in data
    assert "recentTransactions" in data
    assert "budgetProgress" in data
    assert "upcomingBills" in data
    assert "assetLiability" in data


async def test_dashboard_kpis(client: AsyncClient, populated):
    r = await client.get("/api/dashboard?month=2026-04")
    data = r.json()
    assert data["currentMonth"]["income"] == 20000
    assert data["currentMonth"]["expense"] == 5000
    assert data["currentMonth"]["savings"] == 15000


async def test_dashboard_budget_progress(client: AsyncClient, populated):
    r = await client.get("/api/dashboard?month=2026-04")
    bp = r.json()["budgetProgress"]
    assert len(bp) >= 1
    assert bp[0]["budgetAmount"] == 10000
    assert bp[0]["spentAmount"] == 5000


async def test_dashboard_asset_liability(client: AsyncClient, populated):
    r = await client.get("/api/dashboard?month=2026-04")
    al = r.json()["assetLiability"]
    assert al["totalAssets"] > 0
    assert isinstance(al["assets"], list)


# ── Reports ────────────────────────────────────────────────


async def test_reports_month_mode(client: AsyncClient, populated):
    r = await client.get("/api/reports?mode=month&month=2026-04")
    assert r.status_code == 200
    data = r.json()
    assert data["current"]["income"] == 20000
    assert data["current"]["expense"] == 5000
    assert "chartData" in data
    assert "trendData" in data
    assert "expenseByCategory" in data
    assert "cashFlow" in data


async def test_reports_year_mode(client: AsyncClient, populated):
    r = await client.get("/api/reports?mode=year&year=2026")
    assert r.status_code == 200
    data = r.json()
    assert data["current"]["income"] >= 20000
    assert len(data["chartData"]) == 12  # T1..T12


async def test_reports_cash_flow(client: AsyncClient, populated):
    r = await client.get("/api/reports?mode=month&month=2026-04")
    cf = r.json()["cashFlow"]
    assert cf["totalIncome"] == 20000
    assert cf["totalExpense"] == 5000
    assert cf["net"] == 15000


# ── Settings ───────────────────────────────────────────────


async def test_get_settings_empty(client: AsyncClient):
    r = await client.get("/api/settings")
    assert r.status_code == 200
    assert "data" in r.json()


async def test_upsert_settings(client: AsyncClient):
    r = await client.put("/api/settings", json={
        "data": {"userName": "Test User", "currency": "USD"}
    })
    assert r.status_code == 200
    assert r.json()["success"] is True

    r2 = await client.get("/api/settings")
    data = r2.json()["data"]
    assert data["userName"] == "Test User"
    assert data["currency"] == "USD"


async def test_update_existing_setting(client: AsyncClient):
    await client.put("/api/settings", json={"data": {"theme": "light"}})
    await client.put("/api/settings", json={"data": {"theme": "dark"}})
    r = await client.get("/api/settings")
    assert r.json()["data"]["theme"] == "dark"
