"""MCP tools for budgets."""

from datetime import date

from mcp.server.fastmcp import FastMCP
from sqlalchemy import and_, func, select

from app.mcp.db import get_session
from app.models.budget import Budget
from app.models.category import Category
from app.models.transaction import Transaction


def _current_month() -> str:
    d = date.today()
    return f"{d.year}-{d.month:02d}"


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_budget_status(month: str | None = None) -> str:
        """Tình trạng ngân sách tháng: ngân sách vs thực chi theo từng danh mục.
        Format tháng: YYYY-MM."""
        m = month or _current_month()
        start = f"{m}-01"
        end = f"{m}-31"
        async with get_session() as db:
            # Get budgets
            budgets = (
                await db.execute(
                    select(
                        Budget.category_id,
                        Budget.amount,
                        Category.name,
                        Category.icon,
                    )
                    .outerjoin(Category, Budget.category_id == Category.id)
                    .where(Budget.month == m)
                )
            ).all()

            if not budgets:
                return f"Tháng {m}: Chưa đặt ngân sách nào."

            # Get actual spending
            spending = (
                await db.execute(
                    select(
                        Transaction.category_id,
                        func.sum(Transaction.amount).label("total"),
                    )
                    .where(
                        and_(
                            Transaction.type == "expense",
                            Transaction.date >= start,
                            Transaction.date <= end,
                        )
                    )
                    .group_by(Transaction.category_id)
                )
            ).all()
            spent_map = {str(r.category_id): r.total for r in spending}

            lines = [f"Ngân sách tháng {m}:"]
            total_budget = 0.0
            total_spent = 0.0
            for b in budgets:
                cat_name = b.name or "Khác"
                cat_icon = b.icon or "📦"
                spent = spent_map.get(str(b.category_id), 0)
                pct = round((spent / b.amount) * 100) if b.amount > 0 else 0
                status = "VƯỢT" if spent > b.amount else ("Cảnh báo" if pct >= 80 else "OK")
                lines.append(
                    f"- {cat_icon} {cat_name}: {spent:,.0f}/{b.amount:,.0f} VND "
                    f"({pct}%) [{status}]"
                )
                total_budget += b.amount
                total_spent += spent

            overall_pct = round((total_spent / total_budget) * 100) if total_budget > 0 else 0
            lines.append(
                f"\nTổng: {total_spent:,.0f}/{total_budget:,.0f} VND ({overall_pct}%)"
            )
            return "\n".join(lines)
