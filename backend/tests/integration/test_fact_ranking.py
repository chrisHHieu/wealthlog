"""Tests for importance scoring + access tracking on user facts."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


# ── _clamp_importance (pure) ───────────────────────────────────────────────


def test_clamp_importance_valid_range():
    from app.ai.memory.facts import _clamp_importance

    assert _clamp_importance(1) == 1
    assert _clamp_importance(5) == 5
    assert _clamp_importance(10) == 10


def test_clamp_importance_out_of_range():
    from app.ai.memory.facts import _clamp_importance

    assert _clamp_importance(0) == 1
    assert _clamp_importance(-3) == 1
    assert _clamp_importance(11) == 10
    assert _clamp_importance(999) == 10


def test_clamp_importance_float_truncates():
    from app.ai.memory.facts import _clamp_importance

    assert _clamp_importance(7.8) == 7


def test_clamp_importance_invalid_defaults_to_five():
    from app.ai.memory.facts import _clamp_importance

    assert _clamp_importance(None) == 5
    assert _clamp_importance("high") == 5
    assert _clamp_importance(True) == 5  # bool masquerading as int
    assert _clamp_importance([7]) == 5


# ── get_user_facts ordering + access tracking ──────────────────────────────


def _patch_session(db: AsyncSession):
    """Context manager patching memory.get_session to hand back the test session."""
    from app.ai.memory import facts as memory_module

    @asynccontextmanager
    async def _patched():
        yield db

    return patch.object(memory_module, "get_session", _patched)


async def test_get_user_facts_orders_by_importance(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

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
    from app.ai.memory import facts as memory_module

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
    from app.ai.memory import facts as memory_module

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
    from app.ai.memory import facts as memory_module

    db.add(UserFact(fact="only read", category="general", importance=5))
    await db.flush()

    with _patch_session(db):
        await memory_module.get_user_facts(track_access=False)

    row = (await db.execute(select(UserFact))).scalar_one()
    assert row.access_count == 0
    assert row.last_accessed_at is None


async def test_get_user_facts_exposes_importance(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

    db.add(UserFact(fact="big goal", category="goal", importance=9))
    await db.flush()

    with _patch_session(db):
        facts = await memory_module.get_user_facts(track_access=False)

    assert facts[0]["importance"] == 9


# ── save_user_fact persists importance ─────────────────────────────────────


async def test_save_user_fact_persists_importance(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

    with _patch_session(db):
        result = await memory_module.save_user_fact(
            fact="critical fact", category="goal", importance=9,
        )

    assert result["status"] == "saved"
    row = (await db.execute(select(UserFact))).scalar_one()
    assert row.importance == 9


async def test_save_user_fact_default_importance(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

    with _patch_session(db):
        await memory_module.save_user_fact(fact="neutral fact")

    row = (await db.execute(select(UserFact))).scalar_one()
    assert row.importance == 5


# ── _clamp_confidence (alias of _clamp_score) ──────────────────────────────


def test_clamp_confidence_shares_implementation_with_importance():
    """One validator backs both fields — they cannot drift apart."""
    from app.ai.memory.facts import _clamp_confidence, _clamp_importance

    assert _clamp_confidence is _clamp_importance


def test_clamp_confidence_clamps_and_defaults():
    from app.ai.memory.facts import _clamp_confidence

    assert _clamp_confidence(0) == 1
    assert _clamp_confidence(11) == 10
    assert _clamp_confidence(None) == 5
    assert _clamp_confidence("very") == 5


# ── verified_by_user ranking + persistence ─────────────────────────────────


async def test_verified_facts_outrank_unverified_at_equal_importance(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

    db.add(UserFact(
        fact="reviewer guess", category="goal", importance=8,
        verified_by_user=False,
    ))
    db.add(UserFact(
        fact="user confirmed", category="goal", importance=8,
        verified_by_user=True,
    ))
    await db.flush()

    with _patch_session(db):
        facts = await memory_module.get_user_facts(track_access=False)

    assert facts[0]["fact"] == "user confirmed"
    assert facts[1]["fact"] == "reviewer guess"


async def test_get_user_facts_exposes_verified_flag(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

    db.add(UserFact(
        fact="signed off", category="goal", importance=7,
        verified_by_user=True,
    ))
    await db.flush()

    with _patch_session(db):
        facts = await memory_module.get_user_facts(track_access=False)

    assert facts[0]["verified_by_user"] is True


async def test_higher_importance_still_beats_verified(db: AsyncSession):
    """Verified is a tie-breaker, not an override of the primary signal."""
    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

    db.add(UserFact(
        fact="critical guess", category="goal", importance=9,
        verified_by_user=False,
    ))
    db.add(UserFact(
        fact="minor confirmed", category="goal", importance=4,
        verified_by_user=True,
    ))
    await db.flush()

    with _patch_session(db):
        facts = await memory_module.get_user_facts(track_access=False)

    assert facts[0]["fact"] == "critical guess"


async def test_confidence_breaks_ties_when_verified_status_matches(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

    db.add(UserFact(
        fact="low conf", category="goal", importance=7,
        verified_by_user=False, confidence=3,
    ))
    db.add(UserFact(
        fact="high conf", category="goal", importance=7,
        verified_by_user=False, confidence=9,
    ))
    await db.flush()

    with _patch_session(db):
        facts = await memory_module.get_user_facts(track_access=False)

    assert facts[0]["fact"] == "high conf"


async def test_save_user_fact_persists_confidence(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

    with _patch_session(db):
        await memory_module.save_user_fact(
            fact="something", category="general", importance=5, confidence=9,
        )

    row = (await db.execute(select(UserFact))).scalar_one()
    assert row.confidence == 9
    assert row.verified_by_user is False  # only the user-facing tool can flip this


# ── build_facts_prompt verified marker ─────────────────────────────────────


async def test_build_facts_prompt_marks_verified(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

    db.add(UserFact(
        fact="confirmed goal", category="goal", importance=8,
        verified_by_user=True,
    ))
    db.add(UserFact(
        fact="guessed goal", category="goal", importance=8,
        verified_by_user=False,
    ))
    await db.flush()

    with _patch_session(db):
        prompt = await memory_module.build_facts_prompt()

    assert "[✓] (Goal) confirmed goal" in prompt
    assert "- (Goal) guessed goal" in prompt  # no marker on unverified
    # confidence stays internal — no number leaks into the prompt text
    assert "confidence" not in prompt.lower()
