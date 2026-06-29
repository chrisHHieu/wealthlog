"""Resolver lookups — name → ID translation used by the agent's write tools."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.resolvers import resolve_category
from app.models.category import Category


async def _make_category(db: AsyncSession, name: str, icon: str) -> Category:
    cat = Category(name=name, icon=icon, type="expense")
    db.add(cat)
    await db.flush()
    return cat


async def test_resolve_category_exact_and_case_insensitive(db: AsyncSession):
    cat = await _make_category(db, "Food & Dining", "🍜")
    assert await resolve_category(db, "Food & Dining") == cat.id
    assert await resolve_category(db, "food & dining") == cat.id


async def test_resolve_category_strips_leading_icon(db: AsyncSession):
    """The categories resource lists "{icon} {name}", so the agent often passes
    the emoji-decorated form — it must still resolve, not silently miss."""
    cat = await _make_category(db, "Food & Dining", "🍜")
    assert await resolve_category(db, "🍜 Food & Dining") == cat.id


async def test_resolve_category_unknown_returns_none(db: AsyncSession):
    await _make_category(db, "Food & Dining", "🍜")
    assert await resolve_category(db, "Nonexistent") is None
