"""MCP resources — static context for AI to read."""

from mcp.server.fastmcp import FastMCP
from sqlalchemy import select

from app.database import get_session
from app.models.category import Category
from app.models.setting import Setting

_TYPE_LABELS = {"income": "Income", "expense": "Expense", "both": "Income/Expense"}


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
            lines.append(f"Name: {name}")
        if currency and currency != "VND":
            lines.append(f"Currency: {currency}")

        return "\n".join(lines) if lines else "No profile data yet."

    @mcp.resource("wealthlog://categories")
    async def get_categories() -> str:
        """Income/expense categories (up to 100 — tools accept category_name, no ID needed)."""
        async with get_session() as db:
            rows = (
                await db.execute(select(Category).order_by(Category.name).limit(100))
            ).scalars().all()

            if not rows:
                return "No categories yet."

            lines = ["Available categories:"]
            for c in rows:
                t = _TYPE_LABELS.get(c.type.value, c.type.value)
                group = f" [{c.budget_group.value}]" if c.budget_group else ""
                lines.append(f"- {c.icon} {c.name} ({t}){group}")
            if len(rows) == 100:
                lines.append(
                    "\n(First 100 categories shown — there are more, but "
                    "create_transaction still matches by name.)"
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
            "Personal finance management tools (VND by default). "
            "Month format: YYYY-MM. Date format: YYYY-MM-DD.\n\n"
            "## Tool selection priority\n"
            "1. Specialized tools (get_spending_by_category, get_budget_status, "
            "get_financial_summary, get_goals, get_portfolio, search_transactions…) "
            "— fast, pre-formatted.\n"
            "2. Use query_database only when the question is outside specialized-tool scope "
            "(e.g., group by weekday, anomaly detection).\n"
            "3. get_database_schema if you need to re-fetch the DB structure after a migration.\n\n"
            "## Conventions\n"
            "- Amounts are always positive. Income/expense direction is set by `type`.\n"
            "- Money columns are double precision → cast ::numeric before ROUND when writing SQL.\n"
            "- See wealthlog://categories for categories, wealthlog://profile for the user profile."
        )
