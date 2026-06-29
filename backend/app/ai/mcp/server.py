"""WealthLog MCP server — registers tools, resources, and prompts."""

from mcp.server.fastmcp import FastMCP

from app.ai.mcp import prompts, resources
from app.ai.mcp.tools import (
    accounts,
    budgets,
    discovery,
    goals,
    investments,
    reports,
    transactions,
)
from app.config import settings

mcp = FastMCP(
    "WealthLog",
    instructions=(
        "WealthLog MCP server — personal finance management. "
        "Use the tools to query and manage accounts, transactions, budgets, "
        "goals, investments, and financial reports. "
        "Default currency: VND. Month format: YYYY-MM. Date format: YYYY-MM-DD. "
        "Database: PostgreSQL 16."
    ),
    host=settings.mcp_host,
    port=settings.mcp_port,
)

# Register tools
accounts.register(mcp)
transactions.register(mcp)
budgets.register(mcp)
goals.register(mcp)
investments.register(mcp)
reports.register(mcp)
discovery.register(mcp)

# Register resources & prompts
resources.register(mcp)
prompts.register(mcp)
