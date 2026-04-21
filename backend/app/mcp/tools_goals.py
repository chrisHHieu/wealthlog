"""MCP tools for goals."""

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.mcp.db import get_session
from app.models.goal import Goal


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_goals(limit: int = 30) -> str:
        """Lấy danh sách mục tiêu tài chính (tên, loại, tiến độ, deadline).
        - limit: tối đa bao nhiêu mục tiêu (mặc định 30)."""
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
                return "Chưa có mục tiêu nào."

            type_labels = {
                "emergency": "Quỹ khẩn cấp",
                "savings": "Tiết kiệm",
                "purchase": "Mua sắm",
                "investment": "Đầu tư",
                "debt": "Trả nợ",
                "custom": "Tùy chỉnh",
            }
            lines = []
            for g in rows:
                pct = round((g.current_amount / g.target_amount) * 100) if g.target_amount > 0 else 0
                status = "Hoàn thành" if g.is_completed else f"{pct}%"
                goal_type = type_labels.get(g.type.value, g.type.value)
                deadline = f" | Hạn: {g.deadline}" if g.deadline else ""
                remaining = g.target_amount - g.current_amount
                lines.append(
                    f"- {g.icon} {g.name} ({goal_type}): "
                    f"{g.current_amount:,.0f}/{g.target_amount:,.0f} VND [{status}]"
                    f"{deadline}"
                )
                if not g.is_completed and remaining > 0:
                    lines.append(f"  Còn thiếu: {remaining:,.0f} VND")
            if len(rows) == limit:
                lines.append(f"\n(Hiển thị {limit} mục tiêu đầu — tăng limit nếu cần thêm)")
            return "\n".join(lines)
