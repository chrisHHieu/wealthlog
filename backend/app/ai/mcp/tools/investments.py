"""MCP tools for investments."""

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select

from app.database import get_session
from app.models.investment import Investment

_TYPE_LABELS = {
    "stock": "Stock",
    "etf": "ETF",
    "gold": "Gold",
    "realestate": "Real estate",
    "savings": "Savings",
    "crypto": "Crypto",
    "other": "Other",
}


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_portfolio(limit: int = 50) -> str:
        """List the investment portfolio (name, type, quantity, buy/current price, P&L).
        - limit: max number of holdings (default 50)."""
        async with get_session() as db:
            rows = (
                await db.execute(
                    select(Investment)
                    .order_by(Investment.buy_date)
                    .limit(limit)
                )
            ).scalars().all()

            if not rows:
                return "No investments yet."

            lines = []
            total_invested = 0.0
            total_current = 0.0

            for inv in rows:
                invested = inv.quantity * inv.buy_price
                current = inv.quantity * inv.current_price
                pnl = current - invested
                pnl_pct = round((pnl / invested) * 100, 1) if invested > 0 else 0
                total_invested += invested
                total_current += current

                inv_type = _TYPE_LABELS.get(inv.type.value, inv.type.value)
                symbol = f" ({inv.symbol})" if inv.symbol else ""
                sign = "+" if pnl >= 0 else ""
                lines.append(
                    f"- {inv.name}{symbol} [{inv_type}]: "
                    f"{inv.quantity} x {inv.current_price:,.0f} = {current:,.0f} VND "
                    f"({sign}{pnl:,.0f} | {sign}{pnl_pct}%)"
                )

            total_pnl = total_current - total_invested
            total_pct = round((total_pnl / total_invested) * 100, 1) if total_invested > 0 else 0
            sign = "+" if total_pnl >= 0 else ""
            lines.append(
                f"\nPortfolio total: {total_current:,.0f} VND "
                f"(Cost: {total_invested:,.0f} | P&L: {sign}{total_pnl:,.0f} | {sign}{total_pct}%)"
            )
            if len(rows) == limit:
                lines.append(f"(Showing first {limit} — raise limit for more.)")
            return "\n".join(lines)
