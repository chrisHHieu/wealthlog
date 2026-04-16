"""Dashboard aggregation router — mirrors FE DashboardData exactly."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.recurring import RecurringTransaction
from app.models.transaction import Transaction
from app.services.recurring_sync import process_recurring

logger = get_logger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

ASSET_TYPES = {"cash", "bank", "ewallet", "investment", "savings"}
ASSET_LABELS = {
    "cash": "Tiền mặt",
    "bank": "Ngân hàng",
    "ewallet": "Ví điện tử",
    "investment": "Đầu tư",
    "savings": "Tiết kiệm",
}
LIABILITY_LABELS = {"debt": "Nợ vay"}


def _month_str(d: date) -> str:
    return f"{d.year}-{d.month:02d}"


def _prev_month(month: str) -> str:
    y, m = int(month[:4]), int(month[5:7])
    d = date(y, m, 1) - timedelta(days=1)
    return _month_str(d)


@router.get("")
async def get_dashboard(
    period: str = Query("6months"),
    month: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    await process_recurring(db)
    today = date.today()
    selected_month = month if month and len(month) == 7 else _month_str(today)
    prev_month = _prev_month(selected_month)

    # Chart date range
    months_back = {"3months": 2, "12months": 11}.get(period, 5)
    chart_start = date(today.year, today.month, 1)
    for _ in range(months_back):
        chart_start = (chart_start - timedelta(days=1)).replace(day=1)
    chart_start_str = chart_start.strftime("%Y-%m-%d")
    chart_end_str = today.strftime("%Y-%m-%d")

    kpi_start = f"{prev_month}-01"
    kpi_end = f"{selected_month}-31"

    today_str = today.strftime("%Y-%m-%d")
    next30_str = (today + timedelta(days=30)).strftime("%Y-%m-%d")

    # ── Parallel queries ────────────────────────────────────────

    # 1) Chart transactions
    chart_q = select(
        func.substring(Transaction.date, 1, 7).label("month"),
        Transaction.type,
        Transaction.amount,
    ).where(and_(Transaction.date >= chart_start_str, Transaction.date <= chart_end_str))

    # 2) Net worth
    net_q = select(func.coalesce(func.sum(Account.balance), 0)).where(Account.is_active.is_(True))

    # 3) Recent 7 transactions
    recent_q = (
        select(
            Transaction.id,
            Transaction.type,
            Transaction.amount,
            Transaction.description,
            Transaction.date,
            Category.name.label("category_name"),
            Category.icon.label("category_icon"),
            Category.color.label("category_color"),
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())
        .limit(7)
    )

    # 4) KPI transactions (selected + prev month)
    kpi_q = (
        select(
            Transaction.category_id,
            Category.name.label("category_name"),
            Category.icon.label("category_icon"),
            Category.color.label("category_color"),
            Category.budget_group,
            Transaction.amount,
            Transaction.type,
            Transaction.date,
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(and_(Transaction.date >= kpi_start, Transaction.date <= kpi_end))
    )

    # 5) Budget rows for selected month
    budget_q = (
        select(
            Budget.category_id,
            Budget.amount,
            Category.name.label("category_name"),
            Category.icon.label("category_icon"),
            Category.color.label("category_color"),
        )
        .outerjoin(Category, Budget.category_id == Category.id)
        .where(Budget.month == selected_month)
    )

    # 6) Upcoming bills
    bills_q = (
        select(
            RecurringTransaction.id,
            RecurringTransaction.description,
            RecurringTransaction.amount,
            RecurringTransaction.type,
            RecurringTransaction.next_run_date,
            RecurringTransaction.frequency,
            Category.icon.label("category_icon"),
            Category.color.label("category_color"),
        )
        .outerjoin(Category, RecurringTransaction.category_id == Category.id)
        .where(
            and_(
                RecurringTransaction.is_active.is_(True),
                RecurringTransaction.next_run_date >= today_str,
                RecurringTransaction.next_run_date <= next30_str,
            )
        )
        .order_by(RecurringTransaction.next_run_date)
        .limit(5)
    )

    # 7) All active accounts
    accounts_q = select(Account.type, Account.balance).where(Account.is_active.is_(True))

    (
        chart_rows,
        net_worth,
        recent_rows,
        kpi_rows,
        budget_rows,
        bill_rows,
        account_rows,
    ) = (
        (await db.execute(chart_q)).all(),
        (await db.execute(net_q)).scalar() or 0,
        (await db.execute(recent_q)).all(),
        (await db.execute(kpi_q)).all(),
        (await db.execute(budget_q)).all(),
        (await db.execute(bills_q)).all(),
        (await db.execute(accounts_q)).all(),
    )

    # ── Monthly chart ───────────────────────────────────────────
    monthly_map: dict[str, dict[str, float]] = {}
    for m, tx_type, amount in chart_rows:
        if m not in monthly_map:
            monthly_map[m] = {"income": 0, "expense": 0}
        if tx_type == "income":
            monthly_map[m]["income"] += amount
        elif tx_type == "expense":
            monthly_map[m]["expense"] += amount
    monthly_chart = [
        {"month": m, **d} for m, d in sorted(monthly_map.items())
    ]

    # ── KPIs ────────────────────────────────────────────────────
    def _sum_kpi(rows, month_prefix: str, tx_type: str) -> float:
        return sum(r.amount for r in rows if r.date and r.date.startswith(month_prefix) and r.type == tx_type)

    cur_income = _sum_kpi(kpi_rows, selected_month, "income")
    cur_expense = _sum_kpi(kpi_rows, selected_month, "expense")
    prev_income = _sum_kpi(kpi_rows, prev_month, "income")
    prev_expense = _sum_kpi(kpi_rows, prev_month, "expense")

    # ── Category breakdown (selected month expenses) ────────────
    cat_map: dict[str, dict] = {}
    for r in kpi_rows:
        if not (r.date and r.date.startswith(selected_month) and r.type == "expense"):
            continue
        key = str(r.category_id) if r.category_id else "other"
        if key not in cat_map:
            cat_map[key] = {
                "categoryId": key,
                "categoryName": r.category_name or "Khác",
                "categoryIcon": r.category_icon or "📦",
                "categoryColor": r.category_color or "#6b7280",
                "budgetGroup": r.budget_group.value if r.budget_group else None,
                "total": 0,
            }
        cat_map[key]["total"] += r.amount
    category_breakdown = sorted(cat_map.values(), key=lambda c: c["total"], reverse=True)

    # ── 50/30/20 spending by group ──────────────────────────────
    spending = {"needs": 0.0, "wants": 0.0, "savings": 0.0, "unassigned": 0.0}
    for c in category_breakdown:
        group = c["budgetGroup"]
        if group == "needs":
            spending["needs"] += c["total"]
        elif group == "wants":
            spending["wants"] += c["total"]
        else:
            spending["unassigned"] += c["total"]
    spending["savings"] = cur_income - cur_expense

    # ── Recent transactions ─────────────────────────────────────
    recent_transactions = [
        {
            "id": str(r.id),
            "type": r.type,
            "amount": r.amount,
            "description": r.description,
            "date": r.date,
            "categoryName": r.category_name or "Khác",
            "categoryIcon": r.category_icon or "📦",
            "categoryColor": r.category_color or "#6b7280",
        }
        for r in recent_rows
    ]

    # ── Budget progress ─────────────────────────────────────────
    budget_progress = []
    for b in budget_rows:
        spent = cat_map.get(str(b.category_id), {}).get("total", 0)
        budget_progress.append({
            "categoryId": str(b.category_id),
            "categoryName": b.category_name or "Khác",
            "categoryIcon": b.category_icon or "📦",
            "categoryColor": b.category_color or "#6b7280",
            "budgetAmount": b.amount,
            "spentAmount": spent,
        })
    budget_progress.sort(
        key=lambda x: (x["spentAmount"] / x["budgetAmount"]) if x["budgetAmount"] else 0,
        reverse=True,
    )

    # ── Upcoming bills ──────────────────────────────────────────
    upcoming_bills = [
        {
            "id": str(b.id),
            "description": b.description,
            "amount": b.amount,
            "type": b.type,
            "nextRunDate": b.next_run_date,
            "frequency": b.frequency,
            "categoryIcon": b.category_icon or "📋",
            "categoryColor": b.category_color or "#6b7280",
        }
        for b in bill_rows
    ]

    # ── Asset & Liability ───────────────────────────────────────
    grouped: dict[str, float] = {}
    for acc_type, balance in account_rows:
        t = acc_type.value if hasattr(acc_type, "value") else acc_type
        grouped[t] = grouped.get(t, 0) + balance

    assets = []
    liabilities = []
    for t, total in grouped.items():
        if t in ASSET_TYPES:
            assets.append({"type": t, "label": ASSET_LABELS.get(t, t), "total": total})
        else:
            liabilities.append({"type": t, "label": LIABILITY_LABELS.get(t, t), "total": abs(total)})
    assets.sort(key=lambda x: x["total"], reverse=True)
    liabilities.sort(key=lambda x: x["total"], reverse=True)

    return {
        "netWorth": net_worth,
        "selectedMonth": selected_month,
        "currentMonth": {
            "income": cur_income,
            "expense": cur_expense,
            "savings": cur_income - cur_expense,
        },
        "previousMonth": {
            "income": prev_income,
            "expense": prev_expense,
            "savings": prev_income - prev_expense,
        },
        "monthlyChart": monthly_chart,
        "categoryBreakdown": category_breakdown,
        "spendingByGroup": spending,
        "recentTransactions": recent_transactions,
        "budgetProgress": budget_progress,
        "upcomingBills": upcoming_bills,
        "assetLiability": {
            "assets": assets,
            "liabilities": liabilities,
            "totalAssets": sum(a["total"] for a in assets),
            "totalLiabilities": sum(a["total"] for a in liabilities),
        },
    }
