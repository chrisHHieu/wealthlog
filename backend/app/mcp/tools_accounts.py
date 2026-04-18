"""MCP tools for accounts."""

from mcp.server.fastmcp import FastMCP
from sqlalchemy import func, select

from app.mcp.db import get_session
from app.models.account import Account


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_accounts() -> str:
        """Lấy danh sách tất cả tài khoản (tên, loại, số dư, tiền tệ, trạng thái)."""
        async with get_session() as db:
            rows = (await db.execute(select(Account))).scalars().all()
            if not rows:
                return "Chưa có tài khoản nào."
            lines = []
            for a in rows:
                status = "active" if a.is_active else "inactive"
                lines.append(
                    f"- {a.icon} {a.name} ({a.type.value}): "
                    f"{a.balance:,.0f} {a.currency} [{status}]"
                )
            return "\n".join(lines)

    @mcp.tool()
    async def get_account_summary() -> str:
        """Tổng hợp tài sản theo loại (tiền mặt, ngân hàng, ví, đầu tư, tiết kiệm, nợ)."""
        async with get_session() as db:
            rows = (
                await db.execute(
                    select(Account.type, func.sum(Account.balance))
                    .where(Account.is_active.is_(True))
                    .group_by(Account.type)
                )
            ).all()
            if not rows:
                return "Chưa có tài khoản nào."
            labels = {
                "cash": "Tiền mặt",
                "bank": "Ngân hàng",
                "ewallet": "Ví điện tử",
                "investment": "Đầu tư",
                "savings": "Tiết kiệm",
                "debt": "Nợ vay",
            }
            lines = []
            for acc_type, total in rows:
                t = acc_type.value if hasattr(acc_type, "value") else acc_type
                label = labels.get(t, t)
                lines.append(f"- {label}: {total:,.0f} VND")
            return "\n".join(lines)
