"""MCP tools for goals."""

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models.goal import Goal

_TYPE_LABELS = {
    "emergency": "Emergency fund",
    "savings": "Savings",
    "purchase": "Purchase",
    "investment": "Investment",
    "debt": "Debt payoff",
    "custom": "Custom",
}


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_goals(limit: int = 30) -> str:
        """List financial goals (name, type, progress, deadline).
        - limit: max number of goals (default 30)."""
        async with get_session() as db:
            rows = (
                await db.execute(
                    select(Goal)
                    .options(selectinload(Goal.contributions))
                    .order_by(Goal.created_at)
                    .limit(limit)
                )
            ).scalars().all()

            if not rows:
                return "No goals yet."

            lines = []
            for g in rows:
                pct = round((g.current_amount / g.target_amount) * 100) if g.target_amount > 0 else 0
                status = "Completed" if g.is_completed else f"{pct}%"
                goal_type = _TYPE_LABELS.get(g.type.value, g.type.value)
                deadline = f" | Due: {g.deadline}" if g.deadline else ""
                remaining = g.target_amount - g.current_amount
                lines.append(
                    f"- {g.icon} {g.name} ({goal_type}): "
                    f"{g.current_amount:,.0f}/{g.target_amount:,.0f} VND [{status}]"
                    f"{deadline}"
                )
                if not g.is_completed and remaining > 0:
                    lines.append(f"  Remaining: {remaining:,.0f} VND")
            if len(rows) == limit:
                lines.append(f"\n(Showing first {limit} — raise limit for more.)")
            return "\n".join(lines)
