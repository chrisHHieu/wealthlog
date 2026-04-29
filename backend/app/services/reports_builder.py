"""Reports builder — pure aggregation for monthly / yearly report views.

Returns the dict shape consumed by FE ``ReportsData``. The router validates
and dispatches; this module owns the SQL and the math.
"""

from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.transaction import Transaction


def _current_month() -> str:
    d = date.today()
    return f"{d.year}-{d.month:02d}"


def _prev_month_str(month: str) -> str:
    y, m = int(month[:4]), int(month[5:7])
    if m == 1:
        return f"{y - 1}-12"
    return f"{y}-{m - 1:02d}"


def _resolve_window(
    mode: str, month: str | None, year: str | None,
) -> tuple[str, str, str, str]:
    """Compute (cur_start, cur_end, prev_start, prev_end) ISO bounds."""
    today = date.today()
    if mode == "month":
        m = month if month and len(month) == 7 else _current_month()
        cur_start, cur_end = f"{m}-01", f"{m}-31"
        pm = _prev_month_str(m)
        prev_start, prev_end = f"{pm}-01", f"{pm}-31"
    else:
        y = int(year) if year else today.year
        cur_start, cur_end = f"{y}-01-01", f"{y}-12-31"
        prev_start, prev_end = f"{y - 1}-01-01", f"{y - 1}-12-31"
    return cur_start, cur_end, prev_start, prev_end


async def build_reports(
    db: AsyncSession,
    mode: str,
    month: str | None,
    year: str | None,
) -> dict:
    """Run report queries and assemble the FE-ready payload."""
    cur_start, cur_end, prev_start, prev_end = _resolve_window(mode, month, year)

    stmt = (
        select(
            Transaction.type,
            Transaction.amount,
            Transaction.date,
            Transaction.category_id,
            Category.name.label("category_name"),
            Category.icon.label("category_icon"),
            Category.color.label("category_color"),
        )
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(and_(Transaction.date >= prev_start, Transaction.date <= cur_end))
    )
    all_txs = (await db.execute(stmt)).all()

    cur_txs = [t for t in all_txs if cur_start <= t.date <= cur_end]
    prev_txs = [t for t in all_txs if prev_start <= t.date <= prev_end]

    current = _agg(cur_txs)
    previous = _agg(prev_txs)
    chart_data = _chart_data(cur_txs, mode, month)
    trend_data = _trend_data(chart_data)

    cur_exp = _cat_map(cur_txs, "expense")
    prev_exp = _cat_map(prev_txs, "expense")
    cur_inc = _cat_map(cur_txs, "income")
    prev_inc = _cat_map(prev_txs, "income")

    expense_by_category = _comparison(cur_exp, prev_exp, current["expense"])
    income_by_category = _comparison(cur_inc, prev_inc, current["income"])

    cash_flow = {
        "incomeItems": [c for c in income_by_category if c["current"] > 0],
        "expenseItems": [c for c in expense_by_category if c["current"] > 0],
        "totalIncome": current["income"],
        "totalExpense": current["expense"],
        "net": current["savings"],
    }

    top_transactions = [
        {
            "type": t.type,
            "amount": t.amount,
            "date": t.date,
            "categoryName": t.category_name or "Khác",
            "categoryIcon": t.category_icon or "📦",
            "categoryColor": t.category_color or "#6b7280",
        }
        for t in sorted(cur_txs, key=lambda t: t.amount, reverse=True)[:5]
    ]

    return {
        "current": current,
        "previous": previous,
        "chartData": chart_data,
        "trendData": trend_data,
        "expenseByCategory": expense_by_category,
        "incomeByCategory": income_by_category,
        "cashFlow": cash_flow,
        "topTransactions": top_transactions,
    }


def _agg(txs) -> dict:
    inc = sum(t.amount for t in txs if t.type == "income")
    exp = sum(t.amount for t in txs if t.type == "expense")
    sav = inc - exp
    return {
        "income": inc,
        "expense": exp,
        "savings": sav,
        "savingsRate": round((sav / inc) * 100, 1) if inc > 0 else 0,
    }


def _chart_data(cur_txs, mode: str, month: str | None) -> list[dict]:
    chart_map: dict[str, dict[str, float]] = {}

    if mode == "month":
        m = month if month and len(month) == 7 else _current_month()
        y_val, m_val = int(m[:4]), int(m[5:7])
        days = 31 if m_val == 12 else (date(y_val, m_val + 1, 1) - date(y_val, m_val, 1)).days
        for d in range(1, days + 1):
            chart_map[str(d)] = {"income": 0, "expense": 0}
        for t in cur_txs:
            day = str(int(t.date[8:10]))
            if day not in chart_map:
                chart_map[day] = {"income": 0, "expense": 0}
            if t.type == "income":
                chart_map[day]["income"] += t.amount
            elif t.type == "expense":
                chart_map[day]["expense"] += t.amount
    else:
        for m in range(1, 13):
            chart_map[f"T{m}"] = {"income": 0, "expense": 0}
        for t in cur_txs:
            m = int(t.date[5:7])
            key = f"T{m}"
            if t.type == "income":
                chart_map[key]["income"] += t.amount
            elif t.type == "expense":
                chart_map[key]["expense"] += t.amount

    chart = [{"label": k, **v} for k, v in chart_map.items()]
    if mode == "month":
        chart.sort(key=lambda x: int(x["label"]))
    return chart


def _trend_data(chart_data: list[dict]) -> list[dict]:
    cum = 0.0
    out = []
    for d in chart_data:
        cum += d["expense"]
        out.append({"label": d["label"], "cumExpense": cum, "expense": d["expense"]})
    return out


def _cat_map(txs, tx_type: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for t in txs:
        if t.type != tx_type:
            continue
        key = str(t.category_id) if t.category_id else "other"
        if key not in result:
            result[key] = {
                "name": t.category_name or "Khác",
                "icon": t.category_icon or "📦",
                "color": t.category_color or "#6b7280",
                "total": 0,
            }
        result[key]["total"] += t.amount
    return result


def _comparison(cur_m: dict, prev_m: dict, total_cur: float) -> list[dict]:
    all_keys = set(cur_m) | set(prev_m)
    items = []
    for key in all_keys:
        c = cur_m.get(key)
        p = prev_m.get(key)
        cur_val = c["total"] if c else 0
        items.append({
            "categoryId": key,
            "name": (c or p)["name"],
            "icon": (c or p)["icon"],
            "color": (c or p)["color"],
            "current": cur_val,
            "previous": p["total"] if p else 0,
            "pct": round((cur_val / total_cur) * 100, 1) if total_cur > 0 else 0,
        })
    return sorted(items, key=lambda x: x["current"], reverse=True)
