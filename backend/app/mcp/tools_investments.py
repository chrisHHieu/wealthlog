"""MCP tools for investments."""

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select

from app.mcp.db import get_session
from app.models.investment import Investment


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_portfolio(limit: int = 50) -> str:
        """Lấy danh mục đầu tư (tên, loại, số lượng, giá mua, giá hiện tại, lãi/lỗ).
        - limit: tối đa bao nhiêu khoản đầu tư (mặc định 50)."""
        async with get_session() as db:
            rows = (
                await db.execute(
                    select(Investment)
                    .order_by(Investment.buy_date)
                    .limit(limit)
                )
            ).scalars().all()

            if not rows:
                return "Chưa có khoản đầu tư nào."

            type_labels = {
                "stock": "Cổ phiếu",
                "etf": "ETF",
                "gold": "Vàng",
                "realestate": "BĐS",
                "savings": "Tiết kiệm",
                "crypto": "Crypto",
                "other": "Khác",
            }

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

                inv_type = type_labels.get(inv.type.value, inv.type.value)
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
                f"\nTổng portfolio: {total_current:,.0f} VND "
                f"(Vốn: {total_invested:,.0f} | Lãi/Lỗ: {sign}{total_pnl:,.0f} | {sign}{total_pct}%)"
            )
            if len(rows) == limit:
                lines.append(f"(Hiển thị {limit} khoản đầu — tăng limit nếu cần thêm)")
            return "\n".join(lines)
