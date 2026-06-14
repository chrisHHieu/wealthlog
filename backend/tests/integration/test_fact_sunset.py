"""Integration tests for the daily sunset pass (staleness → expiry stamping)."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.memory import decay as decay_module
from app.ai.memory.decay import sunset_stale_facts
from app.ai.memory.fact_scoring import ensure_aware
from app.models.user_fact import UserFact


def _patch_session(db: AsyncSession):
    @asynccontextmanager
    async def _patched():
        yield db

    return patch.object(decay_module, "get_session", _patched)


def _aged(days: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


async def _expiry_of(db: AsyncSession, fact_text: str) -> datetime | None:
    row = (
        await db.execute(select(UserFact).where(UserFact.fact == fact_text))
    ).scalar_one()
    return ensure_aware(row.expires_at)  # SQLite hands back naive datetimes


async def test_floored_stale_fact_gets_expiry_stamp(db: AsyncSession):
    # importance 3, 120 days stale → effective floor; past the 90-day minimum
    db.add(UserFact(
        fact="old trivia", category="general", importance=3, updated_at=_aged(120),
    ))
    await db.flush()

    with _patch_session(db):
        await sunset_stale_facts()

    expiry = await _expiry_of(db, "old trivia")
    assert expiry is not None
    grace_days = (expiry - datetime.now(UTC)).days
    assert 28 <= grace_days <= 30


async def test_verified_facts_are_never_sunset(db: AsyncSession):
    db.add(UserFact(
        fact="confirmed truth", category="goal", importance=3,
        verified_by_user=True, updated_at=_aged(400),
    ))
    await db.flush()

    with _patch_session(db):
        await sunset_stale_facts()

    assert await _expiry_of(db, "confirmed truth") is None


async def test_high_effective_importance_is_not_sunset(db: AsyncSession):
    # importance 9, 100 days stale → effective 6, well above floor
    db.add(UserFact(
        fact="big stale goal", category="goal", importance=9, updated_at=_aged(100),
    ))
    await db.flush()

    with _patch_session(db):
        await sunset_stale_facts()

    assert await _expiry_of(db, "big stale goal") is None


async def test_low_importance_but_fresh_is_not_sunset(db: AsyncSession):
    """Facts born at importance 1-2 must survive the 90-day minimum."""
    db.add(UserFact(
        fact="newborn minor", category="general", importance=1, updated_at=_aged(10),
    ))
    await db.flush()

    with _patch_session(db):
        await sunset_stale_facts()

    assert await _expiry_of(db, "newborn minor") is None


async def test_existing_expiry_is_not_overwritten(db: AsyncSession):
    original = _aged(-5)  # five days from now
    db.add(UserFact(
        fact="already dying", category="general", importance=2,
        updated_at=_aged(200), expires_at=original,
    ))
    await db.flush()

    with _patch_session(db):
        await sunset_stale_facts()

    assert await _expiry_of(db, "already dying") == original
