"""Tests for the row-count-triggered consolidation pass on user_facts."""

import json
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_fact import UserFact


def _patch_session(db: AsyncSession):
    from app.ai.memory import facts as memory_module

    @asynccontextmanager
    async def _patched():
        yield db

    return patch.object(memory_module, "get_session", _patched)


def _seed(db: AsyncSession, n: int) -> None:
    """Seed n placeholder facts so the consolidation gate can be exercised."""
    for i in range(n):
        db.add(UserFact(
            fact=f"placeholder fact {i}",
            category="general",
            importance=5,
        ))


def _haiku_returning(payload: list) -> AsyncMock:
    """Mock the AsyncAnthropic client so messages.create returns the given JSON."""
    resp = MagicMock()
    resp.content = [MagicMock(text=json.dumps(payload))]
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=resp)
    return client


# ── Threshold gate ─────────────────────────────────────────────────────────


async def test_consolidation_skipped_when_under_threshold(db: AsyncSession):
    """Below threshold: no Haiku call at all (cost guardrail)."""
    from app.ai.memory import facts as memory_module

    _seed(db, 50)
    await db.flush()

    haiku = _haiku_returning([])
    with _patch_session(db), \
         patch("app.ai.memory.facts.client_factory", return_value=haiku), \
         patch("app.ai.memory.facts.settings") as s:
        s.anthropic_api_key = "key"
        s.user_fact_consolidation_threshold = 100
        s.agent_review_model = "claude-haiku-4-5-20251001"

        await memory_module._maybe_consolidate(uuid.uuid4())

    haiku.messages.create.assert_not_called()
    rows = (await db.execute(select(UserFact))).scalars().all()
    assert len(rows) == 50  # nothing was touched


async def test_consolidation_skipped_when_no_api_key(db: AsyncSession):
    """No API key → no Haiku call regardless of count."""
    from app.ai.memory import facts as memory_module

    _seed(db, 200)
    await db.flush()

    haiku = _haiku_returning([])
    with _patch_session(db), \
         patch("app.ai.memory.facts.client_factory", return_value=haiku), \
         patch("app.ai.memory.facts.settings") as s:
        s.anthropic_api_key = ""
        s.user_fact_consolidation_threshold = 100
        s.agent_review_model = "claude-haiku-4-5-20251001"

        await memory_module._maybe_consolidate(uuid.uuid4())

    haiku.messages.create.assert_not_called()


# ── _apply_merge_item routing ──────────────────────────────────────────────


async def test_apply_merge_item_keeps_one_removes_others(db: AsyncSession):
    from app.ai.memory import facts as memory_module

    survivor = UserFact(fact="keep me", category="goal", importance=7)
    loser_a = UserFact(fact="dup a", category="goal", importance=6)
    loser_b = UserFact(fact="dup b", category="goal", importance=6)
    db.add(survivor)
    db.add(loser_a)
    db.add(loser_b)
    await db.flush()

    existing = [
        (survivor.id, survivor.fact),
        (loser_a.id, loser_a.fact),
        (loser_b.id, loser_b.fact),
    ]

    with _patch_session(db):
        merged, removed = await memory_module._apply_merge_item(
            {
                "action": "merge",
                "keeps": 1, "removes": [2, 3],
                "fact": "merged text",
                "category": "goal",
                "importance": 9,
                "confidence": 9,
            },
            existing,
        )

    assert merged == 1
    assert removed == 2
    rows = (await db.execute(select(UserFact))).scalars().all()
    assert len(rows) == 1
    assert rows[0].id == survivor.id
    assert rows[0].fact == "merged text"
    assert rows[0].importance == 9


async def test_apply_merge_item_rejects_non_merge_action(db: AsyncSession):
    """Stray 'add' or 'replace' from Haiku must not slip through consolidation."""
    from app.ai.memory import facts as memory_module

    row = UserFact(fact="x", category="general", importance=5)
    db.add(row)
    await db.flush()
    existing = [(row.id, row.fact)]

    with _patch_session(db):
        merged, removed = await memory_module._apply_merge_item(
            {"action": "add", "fact": "sneaky", "category": "general"},
            existing,
        )

    assert (merged, removed) == (0, 0)
    rows = (await db.execute(select(UserFact))).scalars().all()
    assert len(rows) == 1 and rows[0].fact == "x"


async def test_apply_merge_item_rejects_keeps_in_removes(db: AsyncSession):
    """Survivor index must not appear in removes — would delete the row we just updated."""
    from app.ai.memory import facts as memory_module

    a = UserFact(fact="a", category="general", importance=5)
    b = UserFact(fact="b", category="general", importance=5)
    db.add(a)
    db.add(b)
    await db.flush()
    existing = [(a.id, a.fact), (b.id, b.fact)]

    with _patch_session(db):
        merged, removed = await memory_module._apply_merge_item(
            {
                "action": "merge",
                "keeps": 1, "removes": [1, 2],  # 1 in both!
                "fact": "merged",
                "category": "general",
                "importance": 5,
            },
            existing,
        )

    # Only index 2 is a valid remove target after deduping; survivor stays put.
    assert (merged, removed) == (1, 1)
    rows = (await db.execute(select(UserFact))).scalars().all()
    assert len(rows) == 1 and rows[0].id == a.id


async def test_apply_merge_item_skips_invalid_indices(db: AsyncSession):
    """Out-of-range indices yield a no-op rather than raising."""
    from app.ai.memory import facts as memory_module

    row = UserFact(fact="solo", category="general", importance=5)
    db.add(row)
    await db.flush()
    existing = [(row.id, row.fact)]

    with _patch_session(db):
        merged, removed = await memory_module._apply_merge_item(
            {
                "action": "merge",
                "keeps": 99, "removes": [42],
                "fact": "anything",
                "category": "general",
                "importance": 5,
            },
            existing,
        )

    assert (merged, removed) == (0, 0)


# ── End-to-end _maybe_consolidate ──────────────────────────────────────────


async def test_consolidation_reduces_count_when_haiku_proposes_merges(db: AsyncSession):
    """Above threshold + valid merge proposal → count drops by removed-row count."""
    from app.ai.memory import facts as memory_module

    # 105 facts, with rows 1+2+3 known to be near-duplicates.
    db.add(UserFact(
        id=uuid.UUID(int=1),
        fact="Tiết kiệm 50tr cho xe", category="goal", importance=8,
    ))
    db.add(UserFact(
        id=uuid.UUID(int=2),
        fact="Mục tiêu 50 triệu mua xe", category="goal", importance=8,
    ))
    db.add(UserFact(
        id=uuid.UUID(int=3),
        fact="Đang tiết kiệm để mua xe (50tr)", category="goal", importance=8,
    ))
    _seed(db, 102)  # 102 placeholders, total = 105
    await db.flush()

    # Reviewer's '_load_existing_for_review' loads up to 50 rows ordered by
    # updated_at desc — the three above flushed first so they sit near the
    # tail (highest updated_at via test ordering varies). We instead mock
    # the Haiku response with explicit indices that match what the loader
    # will produce: easier to assert by patching _load_existing_for_review.
    fake_existing = [
        (uuid.UUID(int=1), "Tiết kiệm 50tr cho xe"),
        (uuid.UUID(int=2), "Mục tiêu 50 triệu mua xe"),
        (uuid.UUID(int=3), "Đang tiết kiệm để mua xe (50tr)"),
    ]

    haiku = _haiku_returning([{
        "action": "merge",
        "keeps": 1, "removes": [2, 3],
        "fact": "Mục tiêu tiết kiệm 50tr để mua xe",
        "category": "goal",
        "importance": 9,
        "confidence": 9,
    }])

    with _patch_session(db), \
         patch("app.ai.memory.facts._load_existing_for_review",
               AsyncMock(return_value=fake_existing)), \
         patch("app.ai.memory.facts.client_factory", return_value=haiku), \
         patch("app.ai.memory.facts.settings") as s:
        s.anthropic_api_key = "key"
        s.user_fact_consolidation_threshold = 100
        s.agent_review_model = "claude-haiku-4-5-20251001"

        await memory_module._maybe_consolidate(uuid.uuid4())

    rows = (await db.execute(select(UserFact))).scalars().all()
    assert len(rows) == 103  # 105 - 2 removed
    survivor = (await db.execute(
        select(UserFact).where(UserFact.id == uuid.UUID(int=1))
    )).scalar_one()
    assert survivor.fact == "Mục tiêu tiết kiệm 50tr để mua xe"


async def test_consolidation_idempotent_after_count_drops_below_threshold(db: AsyncSession):
    """Second pass right after the first must be a no-op (no Haiku call)."""
    from app.ai.memory import facts as memory_module

    _seed(db, 99)
    await db.flush()

    haiku = _haiku_returning([])
    with _patch_session(db), \
         patch("app.ai.memory.facts.client_factory", return_value=haiku), \
         patch("app.ai.memory.facts.settings") as s:
        s.anthropic_api_key = "key"
        s.user_fact_consolidation_threshold = 100
        s.agent_review_model = "claude-haiku-4-5-20251001"

        await memory_module._maybe_consolidate(uuid.uuid4())
        await memory_module._maybe_consolidate(uuid.uuid4())

    haiku.messages.create.assert_not_called()
