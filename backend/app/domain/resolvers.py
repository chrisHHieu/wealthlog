"""Lookup helpers — translate user-supplied names into IDs.

Case-insensitive on purpose; the agent surfaces names from natural language,
not slugs. Returns ``None`` on miss so callers can branch on it.
"""

import re
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.category import Category

# Leading icon/emoji + symbols run, e.g. the "🍜 " in "🍜 Food & Dining".
_LEADING_ICON = re.compile(r"^[^\w]+", re.UNICODE)


async def resolve_category(db: AsyncSession, category_name: str) -> UUID | None:
    """Find a category by name (case-insensitive). Returns ID or None.

    The categories resource lists each as "{icon} {name}", so the agent often
    copies the emoji into ``category_name`` (e.g. "🍜 Food & Dining"). Try an
    exact match first, then retry with any leading icon/symbols stripped so a
    decorated name still resolves instead of silently leaving the row
    uncategorized.
    """
    name = category_name.strip()
    cid = (
        await db.execute(
            select(Category.id).where(Category.name.ilike(name)).limit(1)
        )
    ).scalar()
    if cid:
        return cid

    stripped = _LEADING_ICON.sub("", name).strip()
    if stripped and stripped != name:
        return (
            await db.execute(
                select(Category.id).where(Category.name.ilike(stripped)).limit(1)
            )
        ).scalar()
    return None


async def resolve_account(db: AsyncSession, account_name: str) -> UUID | None:
    """Find an active account by name. Returns ID or None.

    The agent surfaces account names from natural language and tends to add or
    drop qualifiers (e.g. "TCB Visa Debit" for an account stored as "Visa
    Debit"). So we try an exact case-insensitive match first, then fall back to
    a tolerant substring match — but only when exactly one account matches, so
    an ambiguous guess still misses rather than touching the wrong wallet.
    """
    name = account_name.strip()
    exact = (
        await db.execute(
            select(Account.id).where(
                and_(Account.name.ilike(name), Account.is_active.is_(True))
            ).limit(1)
        )
    ).scalar()
    if exact:
        return exact

    rows = (
        await db.execute(
            select(Account.id, Account.name).where(Account.is_active.is_(True))
        )
    ).all()
    lname = name.lower()
    matches = [
        aid for aid, aname in rows
        if aname and (aname.lower() in lname or lname in aname.lower())
    ]
    return matches[0] if len(matches) == 1 else None


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
