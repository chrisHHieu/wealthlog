"""WealthLog MCP Server entry point."""

from mcp.server.fastmcp import FastMCP

from app.config import settings
from app.mcp import prompts, resources
from app.mcp import tools_accounts, tools_budgets, tools_discovery, tools_goals
from app.mcp import tools_investments, tools_reports, tools_transactions
from app.mcp import tools_transactions_write

mcp = FastMCP(
    "WealthLog",
    instructions=(
        "WealthLog MCP Server — quản lý tài chính cá nhân. "
        "Sử dụng các tool để truy vấn tài khoản, giao dịch, ngân sách, "
        "mục tiêu, đầu tư và báo cáo tài chính. "
        "Tiền tệ mặc định là VND. Format tháng: YYYY-MM. Format ngày: YYYY-MM-DD. "
        "Database: PostgreSQL 16."
    ),
    host=settings.mcp_host,
    port=settings.mcp_port,
)

# Register all tools
tools_accounts.register(mcp)
tools_transactions.register(mcp)
tools_transactions_write.register(mcp)
tools_budgets.register(mcp)
tools_goals.register(mcp)
tools_investments.register(mcp)
tools_reports.register(mcp)
tools_discovery.register(mcp)

# Register resources & prompts
resources.register(mcp)
prompts.register(mcp)
