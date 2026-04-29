"""Account balance mutations — pure domain logic, takes a session.

All MCP write tools and any future REST endpoint that mutates a transaction
should use these helpers instead of inlining ``UPDATE account SET balance = ...``
so the income/expense/transfer signs stay in one place.
"""

from uuid import UUID

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account


async def adjust_balance(db: AsyncSession, account_id: UUID, delta: float) -> None:
    """Add ``delta`` to the account balance (delta may be negative)."""
    await db.execute(
        update(Account)
        .where(Account.id == account_id)
        .values(balance=Account.balance + delta)
    )


async def apply_balance(
    db: AsyncSession,
    tx_type: str,
    amount: float,
    account_id: UUID,
    to_account_id: UUID | None,
) -> None:
    """Apply a transaction's effect on account balance(s)."""
    if tx_type == "income":
        await adjust_balance(db, account_id, amount)
    elif tx_type == "expense":
        await adjust_balance(db, account_id, -amount)
    elif tx_type == "transfer" and to_account_id:
        await adjust_balance(db, account_id, -amount)
        await adjust_balance(db, to_account_id, amount)


async def reverse_balance(
    db: AsyncSession,
    tx_type: str,
    amount: float,
    account_id: UUID,
    to_account_id: UUID | None,
) -> None:
    """Undo a transaction's effect — used by update/delete flows."""
    if tx_type == "income":
        await adjust_balance(db, account_id, -amount)
    elif tx_type == "expense":
        await adjust_balance(db, account_id, amount)
    elif tx_type == "transfer" and to_account_id:
        await adjust_balance(db, account_id, amount)
        await adjust_balance(db, to_account_id, -amount)
