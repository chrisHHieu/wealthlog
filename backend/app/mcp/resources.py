"""MCP resources — static context for AI to read."""

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select

from app.mcp.db import get_session
from app.models.category import Category
from app.models.setting import Setting


def register(mcp: FastMCP) -> None:
    @mcp.resource("wealthlog://profile")
    async def get_profile() -> str:
        """Thông tin người dùng và cài đặt ứng dụng."""
        async with get_session() as db:
            rows = (await db.execute(select(Setting))).scalars().all()
            data = {r.key: r.value for r in rows}

        name = data.get("userName", "Người dùng")
        currency = data.get("currency", "VND")
        language = data.get("language", "vi")
        theme = data.get("theme", "system")

        return (
            f"Tên: {name}\n"
            f"Tiền tệ: {currency}\n"
            f"Ngôn ngữ: {language}\n"
            f"Theme: {theme}\n"
            f"Database: PostgreSQL 16\n"
            f"App: WealthLog - Quản lý tài chính cá nhân"
        )

    @mcp.resource("wealthlog://categories")
    async def get_categories() -> str:
        """Danh sách tất cả danh mục thu chi hiện có."""
        async with get_session() as db:
            rows = (
                await db.execute(select(Category).order_by(Category.name))
            ).scalars().all()

            if not rows:
                return "Chưa có danh mục nào."

            type_labels = {"income": "Thu", "expense": "Chi", "both": "Thu/Chi"}
            lines = ["Danh mục hiện có:"]
            for c in rows:
                t = type_labels.get(c.type.value, c.type.value)
                group = f" [{c.budget_group.value}]" if c.budget_group else ""
                lines.append(f"- {c.icon} {c.name} ({t}){group} | ID: {c.id}")
            return "\n".join(lines)

    @mcp.resource("wealthlog://guide")
    async def get_guide() -> str:
        """Hướng dẫn sử dụng các tool WealthLog MCP."""
        return (
            "# WealthLog MCP Guide\n\n"
            "## Database\n"
            "- PostgreSQL 16, tiền tệ mặc định VND\n"
            "- Format tháng: YYYY-MM (e.g. 2026-04)\n"
            "- Format ngày: YYYY-MM-DD (e.g. 2026-04-17)\n\n"
            "## Tools theo nhóm\n\n"
            "### Tài khoản\n"
            "- get_accounts: danh sách tài khoản + số dư + trạng thái\n"
            "- get_account_summary: tổng hợp theo loại\n\n"
            "### Giao dịch\n"
            "- search_transactions: tìm theo ngày/loại/category/keyword\n"
            "- get_spending_by_category: chi tiêu theo danh mục\n"
            "- get_income_by_category: thu nhập theo danh mục\n"
            "- create_transaction / create_multiple_transactions: tạo giao dịch\n"
            "- update_transaction / delete_transaction: sửa/xóa giao dịch\n"
            "- Dùng resource wealthlog://categories để biết danh mục có sẵn\n"
            "- Dùng get_accounts để biết tài khoản có sẵn\n\n"
            "### Ngân sách\n"
            "- get_budget_status: ngân sách vs thực chi\n\n"
            "### Mục tiêu\n"
            "- get_goals: danh sách + tiến độ\n\n"
            "### Đầu tư\n"
            "- get_portfolio: danh mục + lãi/lỗ\n\n"
            "### Báo cáo\n"
            "- get_financial_summary: tổng hợp so sánh tháng\n"
            "- get_spending_trends: xu hướng nhiều tháng\n"
            "- get_top_expenses: chi tiêu lớn nhất\n"
            "- get_upcoming_bills: hóa đơn sắp tới\n\n"
            "### Nâng cao\n"
            "- get_database_schema: cấu trúc DB\n"
            "- query_database: SQL SELECT tùy ý (PostgreSQL syntax)\n\n"
            "## Thứ tự ưu tiên\n"
            "1. Dùng tool chuyên dụng trước\n"
            "2. Nếu không đủ → get_database_schema để hiểu cấu trúc\n"
            "3. Cuối cùng → query_database với SQL tùy ý"
        )
