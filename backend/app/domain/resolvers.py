"""Lookup helpers — translate user-supplied names into IDs.

Case-insensitive on purpose; the agent surfaces names from natural language,
not slugs. Returns ``None`` on miss so callers can branch on it.
"""

from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.category import Category


async def resolve_category(db: AsyncSession, category_name: str) -> UUID | None:
    """Find a category by name (case-insensitive). Returns ID or None."""
    return (
        await db.execute(
            select(Category.id).where(Category.name.ilike(category_name)).limit(1)
        )
    ).scalar()


async def resolve_account(db: AsyncSession, account_name: str) -> UUID | None:
    """Find an active account by name (case-insensitive). Returns ID or None."""
    return (
        await db.execute(
            select(Account.id).where(
                and_(Account.name.ilike(account_name), Account.is_active.is_(True))
            ).limit(1)
        )
    ).scalar()


async def get_default_account(db: AsyncSession) -> UUID | None:
    """Return the oldest active account ID — used as the implicit default."""
    return (
        await db.execute(
            select(Account.id)
            .where(Account.is_active.is_(True))
            .order_by(Account.created_at)
            .limit(1)
        )
    ).scalar()
