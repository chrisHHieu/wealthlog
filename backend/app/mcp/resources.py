"""MCP resources — static context for AI to read."""

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select

from app.mcp.db import get_session
from app.models.category import Category
from app.models.setting import Setting


def register(mcp: FastMCP) -> None:
    @mcp.resource("wealthlog://profile")
    async def get_profile() -> str:
        """User-specific context: name and non-default currency.

        Static facts (language, theme, DB type, app name) are covered in the
        agent's system prompt — no point re-fetching them here just to bloat
        the cached prompt block.
        """
        async with get_session() as db:
            rows = (await db.execute(select(Setting))).scalars().all()
            data = {r.key: r.value for r in rows}

        name = (data.get("userName") or "").strip()
        currency = (data.get("currency") or "VND").strip()

        lines = []
        if name:
            lines.append(f"Tên: {name}")
        if currency and currency != "VND":
            lines.append(f"Tiền tệ: {currency}")

        return "\n".join(lines) if lines else "Chưa có thông tin hồ sơ."

    @mcp.resource("wealthlog://categories")
    async def get_categories() -> str:
        """Danh sách danh mục thu chi (tối đa 100 — tools nhận category_name, không cần ID)."""
        async with get_session() as db:
            rows = (
                await db.execute(select(Category).order_by(Category.name).limit(100))
            ).scalars().all()

            if not rows:
                return "Chưa có danh mục nào."

            type_labels = {"income": "Thu", "expense": "Chi", "both": "Thu/Chi"}
            lines = ["Danh mục hiện có:"]
            for c in rows:
                t = type_labels.get(c.type.value, c.type.value)
                group = f" [{c.budget_group.value}]" if c.budget_group else ""
                lines.append(f"- {c.icon} {c.name} ({t}){group}")
            if len(rows) == 100:
                lines.append(
                    "\n(Đã cắt 100 danh mục đầu — còn thêm, nhưng create_transaction "
                    "vẫn tự match theo tên)"
                )
            return "\n".join(lines)

    @mcp.resource("wealthlog://guide")
    async def get_guide() -> str:
        """Short cheat-sheet for external MCP clients (Claude Desktop, Inspector).

        NOT preloaded into the WealthLog chat agent — that agent already has
        tool schemas + a system prompt covering the same ground. This resource
        is only useful when a standalone MCP client connects via stdio/SSE
        and needs a quick orientation.
        """
        return (
            "# WealthLog MCP\n"
            "Tools quản lý tài chính cá nhân (VND mặc định). "
            "Format tháng: YYYY-MM. Format ngày: YYYY-MM-DD.\n\n"
            "## Thứ tự ưu tiên khi chọn tool\n"
            "1. Tool chuyên dụng (get_spending_by_category, get_budget_status, "
            "get_financial_summary, get_goals, get_portfolio, search_transactions…) "
            "— nhanh, kết quả đã format.\n"
            "2. Chỉ dùng query_database khi câu hỏi vượt ngoài scope "
            "(vd: group by thứ trong tuần, anomaly detection).\n"
            "3. get_database_schema nếu cần re-fetch cấu trúc DB sau migration.\n\n"
            "## Quy ước\n"
            "- Tiền: luôn dương. Chiều in/out xác định qua `type`.\n"
            "- Cột tiền là double precision → cast ::numeric trước ROUND khi viết SQL.\n"
            "- Xem wealthlog://categories cho danh mục, wealthlog://profile cho hồ sơ user."
        )
