"""Tests for the daily dreaming pass over expired facts and overdue commitments."""

import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.memory import dreaming
from app.models.user_commitment import UserCommitment
from app.models.user_fact import UserFact


def _factory(db: AsyncSession):
    @asynccontextmanager
    async def _f():
        yield db

    return _f


def _model_returning(payload: list) -> AsyncMock:
    """Mock the AsyncAnthropic client so messages.create returns the given JSON."""
    resp = MagicMock()
    resp.content = [MagicMock(text=json.dumps(payload))]
    client = AsyncMock()
    client.messages.create = AsyncMock(return_value=resp)
    return client


def _expired_goal(db: AsyncSession, days_ago: int = 3) -> UserFact:
    row = UserFact(
        fact="Tiết kiệm 50tr mua xe trước tháng 6/2026",
        category="goal",
        importance=8,
        expires_at=datetime.now(UTC) - timedelta(days=days_ago),
    )
    db.add(row)
    return row


def _overdue_commitment(db: AsyncSession) -> UserCommitment:
    row = UserCommitment(
        text="Thiết lập auto-savings 3tr/tháng",
        status="pending",
        due_by=datetime.now(UTC) - timedelta(days=5),
    )
    db.add(row)
    return row


def _run_patches(client: AsyncMock, api_key: str = "key"):
    """Patch model plumbing + evidence tools so no network/API is touched."""
    settings_patch = patch("app.ai.memory.dreaming.settings")
    patches = [
        settings_patch,
        patch("app.ai.memory.dreaming.anthropic.AsyncAnthropic", return_value=client),
        patch(
            "app.ai.memory.dreaming.get_structured_model",
            AsyncMock(return_value="claude-haiku-4-5-20251001"),
        ),
        patch("app.ai.memory.dreaming.resolve_client_kwargs", lambda model: {}),
        patch(
            "app.ai.memory.dreaming.execute_tool",
            AsyncMock(return_value=("[mock financial data]", False)),
        ),
    ]

    class _Ctx:
        def __enter__(self):
            for p in patches:
                started = p.start()
                if p is settings_patch:
                    started.anthropic_api_key = api_key
                    started.deepseek_api_key = ""
            return self

        def __exit__(self, *exc):
            for p in patches:
                p.stop()
            return False

    return _Ctx()


# ── Gates ──────────────────────────────────────────────────────────────────


async def test_dreaming_skips_when_nothing_expired(db: AsyncSession):
    """Evergreen and future-expiry facts trigger no model call (cost guardrail)."""
    db.add(UserFact(fact="evergreen", category="general", importance=5))
    db.add(UserFact(
        fact="still active",
        category="goal",
        importance=5,
        expires_at=datetime.now(UTC) + timedelta(days=30),
    ))
    await db.flush()

    client = _model_returning([])
    with _run_patches(client):
        await dreaming.run_dreaming_pass(session_factory=_factory(db))

    client.messages.create.assert_not_called()


async def test_dreaming_skips_without_api_key(db: AsyncSession):
    _expired_goal(db)
    await db.flush()

    client = _model_returning([])
    with _run_patches(client, api_key=""):
        await dreaming.run_dreaming_pass(session_factory=_factory(db))

    client.messages.create.assert_not_called()


# ── Rewrite ────────────────────────────────────────────────────────────────


async def test_rewrite_updates_text_and_clears_expiry(db: AsyncSession):
    """A rewritten fact becomes evergreen history, out of the purge's reach."""
    row = _expired_goal(db)
    await db.flush()

    client = _model_returning([{
        "action": "rewrite",
        "index": 1,
        "fact": "Đã tiết kiệm được 42tr trong mục tiêu 50tr mua xe (6/2026) — chưa đạt",
        "importance": 5,
        "confidence": 7,
        "topics": ["mục tiêu", "tiết kiệm"],
    }])
    with _run_patches(client):
        await dreaming.run_dreaming_pass(session_factory=_factory(db))

    updated = (await db.execute(select(UserFact).where(UserFact.id == row.id))).scalar_one()
    assert "42tr" in updated.fact
    assert updated.expires_at is None
    assert updated.importance == 5
    assert updated.confidence == 7
    assert updated.category == "goal"  # category preserved


async def test_drop_leaves_fact_expired_for_purge(db: AsyncSession):
    row = _expired_goal(db)
    await db.flush()

    client = _model_returning([{"action": "drop", "index": 1}])
    with _run_patches(client):
        await dreaming.run_dreaming_pass(session_factory=_factory(db))

    untouched = (await db.execute(select(UserFact).where(UserFact.id == row.id))).scalar_one()
    assert untouched.fact == row.fact
    assert untouched.expires_at is not None  # purge will delete it


# ── Commitments ────────────────────────────────────────────────────────────


async def test_resolve_commitment_marks_done(db: AsyncSession):
    overdue = _overdue_commitment(db)
    fresh = UserCommitment(
        text="Xem lại bảo hiểm",
        status="pending",
        due_by=datetime.now(UTC) + timedelta(days=10),
    )
    db.add(fresh)
    await db.flush()

    client = _model_returning([
        {"action": "resolve_commitment", "index": 1, "status": "done"},
    ])
    with _run_patches(client):
        await dreaming.run_dreaming_pass(session_factory=_factory(db))

    resolved = (
        await db.execute(select(UserCommitment).where(UserCommitment.id == overdue.id))
    ).scalar_one()
    assert resolved.status == "done"
    # Non-overdue commitment was never a candidate and stays pending.
    untouched = (
        await db.execute(select(UserCommitment).where(UserCommitment.id == fresh.id))
    ).scalar_one()
    assert untouched.status == "pending"


# ── Malformed model output ─────────────────────────────────────────────────


async def test_invalid_items_are_skipped_safely(db: AsyncSession):
    """Bad indices, unknown actions, and junk statuses must not change state."""
    fact = _expired_goal(db)
    commitment = _overdue_commitment(db)
    await db.flush()

    client = _model_returning([
        {"action": "rewrite", "index": 99, "fact": "out of range"},
        {"action": "rewrite", "index": 1, "fact": ""},          # empty text
        {"action": "resolve_commitment", "index": 1, "status": "maybe"},
        {"action": "explode", "index": 1},
        "not even a dict",
    ])
    with _run_patches(client):
        await dreaming.run_dreaming_pass(session_factory=_factory(db))

    same_fact = (await db.execute(select(UserFact).where(UserFact.id == fact.id))).scalar_one()
    assert same_fact.fact == fact.fact and same_fact.expires_at is not None
    same_commitment = (
        await db.execute(select(UserCommitment).where(UserCommitment.id == commitment.id))
    ).scalar_one()
    assert same_commitment.status == "pending"
