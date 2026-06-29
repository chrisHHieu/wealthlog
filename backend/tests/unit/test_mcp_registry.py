"""Registration guard for the MCP surface.

Bug history: tools were defined inside ``register_*`` functions but missing the
``@mcp.tool()`` decorator (create_transaction, create_multiple_transactions,
search_transactions). They silently never registered while the system prompt
kept advertising them. This test pins the expected tool/resource/prompt names so
a dropped decorator fails CI instead of shipping a dead tool.
"""

from app.ai.mcp.server import mcp
from app.config import settings

EXPECTED_TOOLS = {
    # accounts
    "get_accounts", "get_account_summary",
    # transactions — read
    "search_transactions", "get_spending_by_category", "get_income_by_category",
    # transactions — write
    "create_transaction", "create_multiple_transactions",
    "update_transaction", "update_multiple_transactions",
    "delete_transaction", "delete_multiple_transactions",
    # budgets / goals / investments
    "get_budget_status", "get_goals", "get_portfolio",
    # reports
    "get_financial_summary", "get_spending_trends", "get_top_expenses",
    "get_upcoming_bills",
    # discovery
    "get_database_schema", "query_database",
    # memory
    "list_my_facts", "forget_fact", "edit_fact", "verify_fact",
    "list_commitments", "complete_commitment", "dismiss_commitment",
}

# Web tools register only when a Tavily key is configured (cross-provider,
# optional). Mirror that gating so the guard passes with or without the key.
if settings.tavily_api_key:
    EXPECTED_TOOLS |= {"web_search", "web_extract"}


async def test_all_expected_tools_are_registered():
    registered = {t.name for t in await mcp.list_tools()}
    missing = EXPECTED_TOOLS - registered
    assert not missing, f"tools defined but not registered (missing @mcp.tool()?): {missing}"


async def test_no_unexpected_tools_registered():
    """A new tool must be added to EXPECTED_TOOLS — keeps the surface curated."""
    registered = {t.name for t in await mcp.list_tools()}
    unexpected = registered - EXPECTED_TOOLS
    assert not unexpected, f"undocumented tools — add to EXPECTED_TOOLS: {unexpected}"


async def test_every_tool_has_a_description():
    """Descriptions are the contract the model selects against — none may be blank."""
    blank = [t.name for t in await mcp.list_tools() if not (t.description or "").strip()]
    assert not blank, f"tools missing a description: {blank}"
