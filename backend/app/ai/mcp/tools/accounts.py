"""MCP tools for accounts."""

from mcp.server.fastmcp import FastMCP
from sqlalchemy import func, select

from app.database import get_session
from app.models.account import Account

_TYPE_LABELS = {
    "cash": "Cash",
    "bank": "Bank",
    "ewallet": "E-wallet",
    "investment": "Investment",
    "savings": "Savings",
    "debt": "Debt",
}


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def get_accounts(
        include_inactive: bool = False,
        limit: int = 50,
    ) -> str:
        """List accounts (name, type, balance, currency, status).
        - include_inactive: default False (active accounts only).
          Set True only when the user explicitly asks about closed accounts.
        - limit: max number of accounts to return (default 50)."""
        async with get_session() as db:
            stmt = select(Account)
            if not include_inactive:
                stmt = stmt.where(Account.is_active.is_(True))
            stmt = stmt.order_by(Account.created_at).limit(limit)
            rows = (await db.execute(stmt)).scalars().all()
            if not rows:
                return "No accounts yet."
            lines = []
            for a in rows:
                status = "active" if a.is_active else "inactive"
                lines.append(
                    f"- {a.icon} {a.name} ({a.type.value}): "
                    f"{a.balance:,.0f} {a.currency} [{status}]"
                )
            if len(rows) == limit:
                lines.append(f"\n(Showing first {limit} — raise limit for more.)")
            return "\n".join(lines)

    @mcp.tool()
    async def get_account_summary() -> str:
        """Aggregate balance by account type (cash, bank, e-wallet, investment, savings, debt)."""
        async with get_session() as db:
            rows = (
                await db.execute(
                    select(Account.type, func.sum(Account.balance))
                    .where(Account.is_active.is_(True))
                    .group_by(Account.type)
                )
            ).all()
            if not rows:
                return "No accounts yet."
            lines = []
            for acc_type, total in rows:
                t = acc_type.value if hasattr(acc_type, "value") else acc_type
                label = _TYPE_LABELS.get(t, t)
                lines.append(f"- {label}: {total:,.0f} VND")
            return "\n".join(lines)
