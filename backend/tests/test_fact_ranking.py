"""Tests for importance scoring + access tracking on user facts."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# ── _clamp_importance (pure) ───────────────────────────────────────────────


def test_clamp_importance_valid_range():
    from app.services.memory import _clamp_importance

    assert _clamp_importance(1) == 1
    assert _clamp_importance(5) == 5
    assert _clamp_importance(10) == 10


def test_clamp_importance_out_of_range():
    from app.services.memory import _clamp_importance

    assert _clamp_importance(0) == 1
    assert _clamp_importance(-3) == 1
    assert _clamp_importance(11) == 10
    assert _clamp_importance(999) == 10


def test_clamp_importance_float_truncates():
    from app.services.memory import _clamp_importance

    assert _clamp_importance(7.8) == 7


def test_clamp_importance_invalid_defaults_to_five():
    from app.services.memory import _clamp_importance

    assert _clamp_importance(None) == 5
    assert _clamp_importance("high") == 5
    assert _clamp_importance(True) == 5  # bool masquerading as int
    assert _clamp_importance([7]) == 5


# ── get_user_facts ordering + access tracking ──────────────────────────────


def _patch_session(db: AsyncSession):
    """Context manager patching memory.get_session to hand back the test session."""
    from app.services import memory as memory_module

    @asynccontextmanager
    async def _patched():
        yield db

    return patch.object(memory_module, "get_session", _patched)


async def test_get_user_facts_orders_by_importance(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.services import memory as memory_module

    db.add(UserFact(fact="minor detail", category="general", importance=2))
    db.add(UserFact(fact="core goal", category="goal", importance=9))
    db.add(UserFact(fact="mid habit", category="habit", importance=6))
    await db.flush()

    with _patch_session(db):
        facts = await memory_module.get_user_facts()

    ordered = [f["fact"] for f in facts]
    assert ordered == ["core goal", "mid habit", "minor detail"]


async def test_get_user_facts_tiebreaks_on_recent_access(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.services import memory as memory_module

    now = datetime.now(timezone.utc)
    db.add(UserFact(fact="never accessed", category="general", importance=5))
    db.add(UserFact(fact="accessed recently", category="general", importance=5,
                    last_accessed_at=now))
    db.add(UserFact(fact="accessed long ago", category="general", importance=5,
                    last_accessed_at=now - timedelta(days=10)))
    await db.flush()

    with _patch_session(db):
        facts = await memory_module.get_user_facts(track_access=False)

    ordered = [f["fact"] for f in facts]
    assert ordered[0] == "accessed recently"
    assert ordered[1] == "accessed long ago"
    assert ordered[2] == "never accessed"


async def test_get_user_facts_bumps_access_count(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.services import memory as memory_module

    db.add(UserFact(fact="a", category="general", importance=5))
    db.add(UserFact(fact="b", category="general", importance=5))
    await db.flush()

    with _patch_session(db):
        await memory_module.get_user_facts()

    rows = (await db.execute(select(UserFact))).scalars().all()
    for r in rows:
        assert r.access_count == 1
        assert r.last_accessed_at is not None


async def test_get_user_facts_track_access_disabled(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.services import memory as memory_module

    db.add(UserFact(fact="only read", category="general", importance=5))
    await db.flush()

    with _patch_session(db):
        await memory_module.get_user_facts(track_access=False)

    row = (await db.execute(select(UserFact))).scalar_one()
    assert row.access_count == 0
    assert row.last_accessed_at is None


async def test_get_user_facts_exposes_importance(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.services import memory as memory_module

    db.add(UserFact(fact="big goal", category="goal", importance=9))
    await db.flush()

    with _patch_session(db):
        facts = await memory_module.get_user_facts(track_access=False)

    assert facts[0]["importance"] == 9


# ── save_user_fact persists importance ─────────────────────────────────────


async def test_save_user_fact_persists_importance(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.services import memory as memory_module

    with _patch_session(db):
        result = await memory_module.save_user_fact(
            fact="critical fact", category="goal", importance=9,
        )

    assert result["status"] == "saved"
    row = (await db.execute(select(UserFact))).scalar_one()
    assert row.importance == 9


async def test_save_user_fact_default_importance(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.services import memory as memory_module

    with _patch_session(db):
        await memory_module.save_user_fact(fact="neutral fact")

    row = (await db.execute(select(UserFact))).scalar_one()
    assert row.importance == 5
