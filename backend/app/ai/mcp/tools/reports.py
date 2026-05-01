"""MCP tools for reports and dashboard insights."""

from datetime import date, timedelta

from mcp.server.fastmcp import FastMCP
from sqlalchemy import and_, func, select

from app.core.time import current_month, month_range
from app.database import get_session
from app.models.account import Account
from app.models.category import Category
from app.models.recurring import RecurringTransaction
from app.models.transaction import Transaction

_TYPE_LABELS = {"income": "Income", "expense": "Expense", "transfer": "Transfer"}
_FREQ_LABELS = {
    "daily": "Daily",
    "weekly": "Weekly",
    "monthly": "Monthly",
    "yearly": "Yearly",
}


def _prev_month(month: str) -> str:
    y, m = int(month[:4]), int(month[5:7])
    d = date(y, m, 1) - timedelta(days=1)
    return f"{d.year}-{d.month:02d}"


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_financial_summary(month: str | None = None) -> str:
        """Financial overview: net worth, current vs previous month income/expense,
        and savings rate. Month format: YYYY-MM."""
        m = month or current_month()
        pm = _prev_month(m)
        async with get_session() as db:
            net_worth = (
                await db.execute(
                    select(func.coalesce(func.sum(Account.balance), 0)).where(
                        Account.is_active.is_(True)
                    )
                )
            ).scalar()

            all_start, _ = month_range(pm)
            _, all_end = month_range(m)
            rows = (
                await db.execute(
                    select(Transaction.type, Transaction.amount, Transaction.date).where(
                        and_(Transaction.date >= all_start, Transaction.date <= all_end)
                    )
                )
            ).all()

            cur_income = sum(r.amount for r in rows if r.date.startswith(m) and r.type == "income")
            cur_expense = sum(r.amount for r in rows if r.date.startswith(m) and r.type == "expense")
            prev_income = sum(r.amount for r in rows if r.date.startswith(pm) and r.type == "income")
            prev_expense = sum(r.amount for r in rows if r.date.startswith(pm) and r.type == "expense")

            cur_savings = cur_income - cur_expense
            prev_savings = prev_income - prev_expense
            rate = round((cur_savings / cur_income) * 100, 1) if cur_income > 0 else 0

            inc_change = cur_income - prev_income
            exp_change = cur_expense - prev_expense
            inc_sign = "+" if inc_change >= 0 else ""
            exp_sign = "+" if exp_change >= 0 else ""

            return (
                f"Financial summary for {m}:\n"
                f"- Net worth: {net_worth:,.0f} VND\n"
                f"- Income: {cur_income:,.0f} VND ({inc_sign}{inc_change:,.0f} vs prev month)\n"
                f"- Expense: {cur_expense:,.0f} VND ({exp_sign}{exp_change:,.0f} vs prev month)\n"
                f"- Savings: {cur_savings:,.0f} VND (rate: {rate}%)\n"
                f"\nPrev month ({pm}): Income {prev_income:,.0f} | "
                f"Expense {prev_expense:,.0f} | Savings {prev_savings:,.0f}"
            )

    @mcp.tool()
    async def get_spending_trends(months: int = 6) -> str:
        """Income/expense trend over recent months (default 6)."""
        today = date.today()
        start = date(today.year, today.month, 1)
        for _ in range(months - 1):
            start = (start - timedelta(days=1)).replace(day=1)
        start_str = start.strftime("%Y-%m-%d")
        end_str = today.strftime("%Y-%m-%d")

        async with get_session() as db:
            rows = (
                await db.execute(
                    select(
                        func.substring(Transaction.date, 1, 7).label("month"),
                        Transaction.type,
                        func.sum(Transaction.amount).label("total"),
                    )
                    .where(and_(Transaction.date >= start_str, Transaction.date <= end_str))
                    .group_by("month", Transaction.type)
                    .order_by("month")
                )
            ).all()

            if not rows:
                return "No data."

            monthly: dict[str, dict[str, float]] = {}
            for m, tx_type, total in rows:
                if m not in monthly:
                    monthly[m] = {"income": 0, "expense": 0}
                if tx_type in ("income", "expense"):
                    monthly[m][tx_type] = total

            lines = [f"Trend over the last {months} month(s):"]
            for m in sorted(monthly):
                inc = monthly[m]["income"]
                exp = monthly[m]["expense"]
                sav = inc - exp
                lines.append(
                    f"- {m}: Income {inc:,.0f} | Expense {exp:,.0f} | Savings {sav:,.0f}"
                )
            return "\n".join(lines)

    @mcp.tool()
    async def get_top_expenses(month: str | None = None, limit: int = 10) -> str:
        """Top expense transactions for the month. Month format: YYYY-MM."""
        m = month or current_month()
        start, end = month_range(m)
        async with get_session() as db:
            rows = (
                await db.execute(
                    select(
                        Transaction.amount,
                        Transaction.description,
                        Transaction.date,
                        Category.name.label("cat_name"),
                        Category.icon.label("cat_icon"),
                    )
                    .outerjoin(Category, Transaction.category_id == Category.id)
                    .where(
                        and_(
                            Transaction.type == "expense",
                            Transaction.date >= start,
                            Transaction.date <= end,
                        )
                    )
                    .order_by(Transaction.amount.desc())
                    .limit(min(limit, 20))
                )
            ).all()

            if not rows:
                return f"Month {m}: no expenses."

            lines = [f"Top {len(rows)} expenses for {m}:"]
            for i, r in enumerate(rows, 1):
                cat = f"{r.cat_icon} {r.cat_name}" if r.cat_name else "Uncategorized"
                desc = r.description or ""
                lines.append(f"{i}. {r.amount:,.0f} VND | {cat} | {desc} [{r.date}]")
            return "\n".join(lines)

    @mcp.tool()
    async def get_upcoming_bills() -> str:
        """Recurring bills/transactions due in the next 30 days."""
        today = date.today()
        today_str = today.strftime("%Y-%m-%d")
        next30_str = (today + timedelta(days=30)).strftime("%Y-%m-%d")

        async with get_session() as db:
            rows = (
                await db.execute(
                    select(
                        RecurringTransaction.description,
                        RecurringTransaction.amount,
                        RecurringTransaction.type,
                        RecurringTransaction.next_run_date,
                        RecurringTransaction.frequency,
                        Category.name.label("cat_name"),
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
                )
            ).all()

            if not rows:
                return "No bills due in the next 30 days."

            lines = ["Upcoming bills (30 days):"]
            for r in rows:
                t = _TYPE_LABELS.get(r.type, r.type)
                freq_key = r.frequency.value if hasattr(r.frequency, "value") else r.frequency
                f = _FREQ_LABELS.get(freq_key, "")
                cat = r.cat_name or ""
                lines.append(
                    f"- [{r.next_run_date}] {r.description}: {r.amount:,.0f} VND ({t}) | {f} | {cat}"
                )
            return "\n".join(lines)

    @mcp.tool()
    async def get_monthly_digest() -> str:
        """Return the latest AI-generated monthly financial digest.

        The digest contains an overall financial summary, budget status, goal
        progress, investment overview, and 3 recommended actions.

        NOTE: Returns CACHED data from the last generation — may be days or weeks
        old. Use live tools (get_financial_summary, get_budget_status, get_goals)
        for current numbers. Call this only when the user explicitly asks for the
        monthly report, a general overview, or what actions to take this month.
        """
        from app.ai.digest import get_latest_digest  # lazy — avoids circular import
        digest = await get_latest_digest()
        if not digest:
            return "Chưa có báo cáo tháng nào. Hãy tạo báo cáo tháng trong phần Cài đặt → Báo cáo tháng."
        return (
            f"[Báo cáo tháng {digest.generated_for_month} — "
            f"tạo lúc {digest.created_at.strftime('%d/%m/%Y %H:%M')}]\n\n"
            + digest.content
        )
