"""Search and aggregation MCP tools for transactions."""

from mcp.server.fastmcp import FastMCP
from sqlalchemy import and_, func, select

from app.ai.mcp.tools.transaction_constants import TYPE_LABELS as _TYPE_LABELS
from app.ai.mcp.tools.transaction_constants import VALID_TYPES as _VALID_TYPES
from app.core.time import current_month, month_range
from app.database import get_session
from app.models.category import Category
from app.models.transaction import Transaction


def register_search_tools(mcp: FastMCP) -> None:
    async def search_transactions(
        start_date: str | None = None,
        end_date: str | None = None,
        type: str | None = None,
        category_name: str | None = None,
        keyword: str | None = None,
        limit: int = 20,
    ) -> str:
        """Search transactions by date range, type (income/expense/transfer),
        category name, or keyword. Date format: YYYY-MM-DD. Default: latest 20."""
        if type is not None and type not in _VALID_TYPES:
            return f"Error: type must be one of {_VALID_TYPES}."
        async with get_session() as db:
            stmt = (
                select(
                    Transaction.type,
                    Transaction.amount,
                    Transaction.description,
                    Transaction.date,
                    Category.name.label("cat_name"),
                    Category.icon.label("cat_icon"),
                )
                .outerjoin(Category, Transaction.category_id == Category.id)
            )
            conditions = []
            if start_date:
                conditions.append(Transaction.date >= start_date)
            if end_date:
                conditions.append(Transaction.date <= end_date)
            if type:
                conditions.append(Transaction.type == type)
            if category_name:
                conditions.append(Category.name.ilike(f"%{category_name}%"))
            if keyword:
                conditions.append(Transaction.description.ilike(f"%{keyword}%"))
            if conditions:
                stmt = stmt.where(and_(*conditions))

            effective_limit = min(limit, 50)
            stmt = stmt.order_by(Transaction.date.desc()).limit(effective_limit)
            rows = (await db.execute(stmt)).all()

            if not rows:
                return "No transactions found."

            lines = []
            for r in rows:
                t = _TYPE_LABELS.get(r.type, r.type)
                cat = f"{r.cat_icon} {r.cat_name}" if r.cat_name else "Uncategorized"
                desc = r.description or ""
                lines.append(f"- [{r.date}] {t}: {r.amount:,.0f} VND | {cat} | {desc}")

            if len(rows) == effective_limit:
                lines.append(
                    f"\n(Showing {effective_limit} results — narrow filters or raise "
                    "limit for more.)"
                )
            return "\n".join(lines)

    @mcp.tool()
    async def get_spending_by_category(month: str | None = None, top_n: int = 10) -> str:
        """EXPENSE total per category for the month. Month format: YYYY-MM.
        Counts only type=expense. For income, use get_income_by_category.
        top_n: number of categories shown (default 10; rest grouped as 'Other')."""
        return await _category_aggregation(month, top_n, tx_type="expense", label="Expenses")

    @mcp.tool()
    async def get_income_by_category(month: str | None = None, top_n: int = 10) -> str:
        """INCOME total per category for the month. Month format: YYYY-MM.
        Counts only type=income. For expenses, use get_spending_by_category.
        top_n: number of categories shown (default 10; rest grouped as 'Other')."""
        return await _category_aggregation(month, top_n, tx_type="income", label="Income")


async def _category_aggregation(
    month: str | None,
    top_n: int,
    tx_type: str,
    label: str,
) -> str:
    """Shared body for spending-by-category and income-by-category."""
    m = month or current_month()
    start, end = month_range(m)
    async with get_session() as db:
        rows = (
            await db.execute(
                select(
                    Category.name,
                    Category.icon,
                    func.sum(Transaction.amount).label("total"),
                )
                .outerjoin(Category, Transaction.category_id == Category.id)
                .where(
                    and_(
                        Transaction.type == tx_type,
                        Transaction.date >= start,
                        Transaction.date <= end,
                    )
                )
                .group_by(Category.name, Category.icon)
                .order_by(func.sum(Transaction.amount).desc())
            )
        ).all()

        if not rows:
            return f"Month {m}: no {tx_type} recorded."

        total = sum(r.total for r in rows)
        lines = [f"{label} for {m} (total: {total:,.0f} VND):"]
        shown = rows[:top_n]
        rest = rows[top_n:]
        for r in shown:
            name = r.name or "Uncategorized"
            icon = r.icon or "📦"
            pct = round((r.total / total) * 100, 1) if total > 0 else 0
            lines.append(f"- {icon} {name}: {r.total:,.0f} VND ({pct}%)")
        if rest:
            rest_total = sum(r.total for r in rest)
            rest_pct = round((rest_total / total) * 100, 1) if total > 0 else 0
            lines.append(
                f"- 📦 Other ({len(rest)} categories): {rest_total:,.0f} VND ({rest_pct}%)"
            )
        return "\n".join(lines)
