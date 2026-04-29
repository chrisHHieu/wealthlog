"""MCP prompts — quick-action templates for external MCP clients.

Exposed to Claude Desktop / MCP Inspector etc. Bodies describe the analysis
goal rather than hardcoding tool names, so they don't go stale when tools are
renamed or added. The agent picks the right tools from its schema.
"""

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base


def register(mcp: FastMCP) -> None:
    @mcp.prompt()
    def monthly_review(month: str | None = None) -> list[base.Message]:
        """Comprehensive financial review for a single month."""
        m = month or "the current month"
        return [
            base.UserMessage(
                f"Review my finances for {m}. Cover:\n"
                "1. Total income, expense, savings — compared to the previous month.\n"
                "2. Top largest expenses.\n"
                "3. Spending by category (up/down vs previous month).\n"
                "4. Budget status (any over-limit categories, any near the cap).\n"
                "5. Overall assessment and concrete improvement advice.\n\n"
                "Use the available financial tools to fetch real numbers — don't fabricate."
            )
        ]

    @mcp.prompt()
    def budget_advice() -> list[base.Message]:
        """Budget allocation advice based on actual spending patterns."""
        return [
            base.UserMessage(
                "Analyze the last 3 months of spending and recommend a budget:\n"
                "1. Per-category trend across the months.\n"
                "2. Categories that are overspent relative to a healthy share.\n"
                "3. Proposed 50/30/20 allocation (needs/wants/savings).\n"
                "4. Where to cut non-essential spending."
            )
        ]

    @mcp.prompt()
    def goal_planning(goal_name: str | None = None) -> list[base.Message]:
        """Plan toward financial goals."""
        target = f"goal '{goal_name}'" if goal_name else "the active goals"
        return [
            base.UserMessage(
                f"Help me plan to hit {target}:\n"
                "1. Current progress for each goal.\n"
                "2. Monthly amount needed to hit the deadline.\n"
                "3. Given current income/expense — is it realistic?\n"
                "4. Adjustments to suggest if progress is slipping."
            )
        ]

    @mcp.prompt()
    def investment_review() -> list[base.Message]:
        """Review the investment portfolio."""
        return [
            base.UserMessage(
                "Review my investment portfolio:\n"
                "1. Portfolio overview: total value, P&L.\n"
                "2. Asset allocation by type (stocks, gold, crypto, …).\n"
                "3. Largest gainers and losers.\n"
                "4. Rebalance suggestions if any single asset is overconcentrated."
            )
        ]

    @mcp.prompt()
    def financial_health() -> list[base.Message]:
        """Overall financial health check."""
        return [
            base.UserMessage(
                "Check overall financial health:\n"
                "1. Net worth and allocation (cash, bank, investments, debt).\n"
                "2. Savings rate over the last 3 months.\n"
                "3. Is the emergency fund 3-6 months of expenses?\n"
                "4. Debt-to-asset ratio.\n"
                "5. Progress on financial goals.\n"
                "6. Upcoming bills due.\n"
                "7. Overall assessment and prioritized recommendations."
            )
        ]
