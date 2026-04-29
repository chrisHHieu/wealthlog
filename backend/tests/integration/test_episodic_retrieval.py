"""Integration tests for hybrid recency + topic-overlap episodic retrieval."""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatSession
from app.models.session_summary import SessionSummary


def _patch_session(db: AsyncSession):
    from app.ai.memory import episodic as ep

    @asynccontextmanager
    async def _patched():
        yield db

    return patch.object(ep, "get_session", _patched)


async def _add_summary(
    db: AsyncSession,
    *,
    summary: str,
    topics: list[str],
    days_ago: int,
    outcome: str | None = None,
) -> SessionSummary:
    """Seed one session + summary at a controlled age."""
    sess = ChatSession(id=uuid.uuid4(), title="t")
    db.add(sess)
    await db.flush()

    when = datetime.now(timezone.utc) - timedelta(days=days_ago)
    row = SessionSummary(
        session_id=sess.id,
        summary=summary,
        key_topics=topics,
        outcome=outcome,
    )
    db.add(row)
    await db.flush()
    # Force the timestamps so age-ordering is deterministic.
    row.updated_at = when
    row.created_at = when
    await db.flush()
    return row


# ── Recency-only path (back-compat with no query_topics) ──────────────────


async def test_get_recent_summaries_recency_only(db: AsyncSession):
    from app.ai.memory import episodic as ep

    await _add_summary(db, summary="oldest", topics=["a"], days_ago=10)
    await _add_summary(db, summary="middle", topics=["b"], days_ago=5)
    await _add_summary(db, summary="newest", topics=["c"], days_ago=1)

    with _patch_session(db):
        rows = await ep.get_recent_summaries()

    summaries = [r.summary for r in rows]
    assert summaries == ["newest", "middle", "oldest"]


# ── Topic-overlap surfaces older relevant sessions ────────────────────────


async def test_topic_overlap_pulls_old_session_into_window(db: AsyncSession):
    """The "remember when we discussed mua xe" case — old but relevant resurfaces."""
    from app.ai.memory import episodic as ep

    await _add_summary(
        db, summary="bàn về mua xe", topics=["xe", "mua xe"], days_ago=20,
    )
    for i in range(5):
        await _add_summary(
            db, summary=f"budget review {i}",
            topics=["budget", "ngân sách"], days_ago=i,
        )

    with patch("app.ai.memory.episodic.settings") as s, _patch_session(db):
        s.session_summary_max_recent = 5
        s.session_summary_topic_hits = 2

        rows = await ep.get_recent_summaries(query_topics=["xe"])

    surfaced = [r.summary for r in rows]
    assert "bàn về mua xe" in surfaced
    # The recency block still wins the front of the list — topic hits trail.
    assert surfaced[0].startswith("budget review")


async def test_topic_overlap_skipped_when_query_topics_empty(db: AsyncSession):
    """No query → behave exactly like the legacy recency-only retrieval."""
    from app.ai.memory import episodic as ep

    await _add_summary(
        db, summary="old car talk", topics=["xe"], days_ago=20,
    )
    for i in range(5):
        await _add_summary(
            db, summary=f"new {i}", topics=["budget"], days_ago=i,
        )

    with patch("app.ai.memory.episodic.settings") as s, _patch_session(db):
        s.session_summary_max_recent = 5
        s.session_summary_topic_hits = 2

        rows = await ep.get_recent_summaries(query_topics=None)

    summaries = {r.summary for r in rows}
    assert "old car talk" not in summaries  # falls outside the recency window


async def test_topic_overlap_excludes_already_in_recent(db: AsyncSession):
    """Topic hits don't double-count rows that already made the recency cut."""
    from app.ai.memory import episodic as ep

    # All 3 are recent and all match the query — topic block must NOT re-add them.
    await _add_summary(db, summary="a", topics=["xe"], days_ago=1)
    await _add_summary(db, summary="b", topics=["xe"], days_ago=2)
    await _add_summary(db, summary="c", topics=["xe"], days_ago=3)

    with patch("app.ai.memory.episodic.settings") as s, _patch_session(db):
        s.session_summary_max_recent = 5
        s.session_summary_topic_hits = 2

        rows = await ep.get_recent_summaries(query_topics=["xe"])

    summaries = [r.summary for r in rows]
    assert summaries.count("a") == 1
    assert len(summaries) == 3


# ── outcome rendering ─────────────────────────────────────────────────────


async def test_build_summaries_prompt_renders_outcome(db: AsyncSession):
    from app.ai.memory import episodic as ep

    await _add_summary(
        db, summary="long story", topics=["budget"], days_ago=1,
        outcome="Đã lập budget tháng 4 5tr",
    )

    with _patch_session(db):
        prompt = await ep.build_summaries_prompt()

    assert "long story" in prompt
    assert "Outcome: Đã lập budget tháng 4 5tr" in prompt


async def test_build_summaries_prompt_handles_legacy_rows_without_outcome(db: AsyncSession):
    """Pre-migration rows have outcome=NULL — must render cleanly."""
    from app.ai.memory import episodic as ep

    await _add_summary(
        db, summary="legacy row", topics=["x"], days_ago=1, outcome=None,
    )

    with _patch_session(db):
        prompt = await ep.build_summaries_prompt()

    assert "legacy row" in prompt
    assert "Outcome:" not in prompt  # nothing to render


# ── upsert with outcome (and SQLite fallback) ──────────────────────────────


async def test_upsert_summary_writes_outcome(db: AsyncSession):
    from app.ai.memory import episodic as ep

    sess = ChatSession(id=uuid.uuid4(), title="t")
    db.add(sess)
    await db.flush()

    with _patch_session(db):
        await ep._upsert_summary(
            sess.id,
            summary_text="s",
            topics=["t"],
            outcome="decided X",
        )

    row = (await db.execute(select(SessionSummary))).scalar_one()
    assert row.outcome == "decided X"


async def test_upsert_summary_updates_existing_row(db: AsyncSession):
    """Second call should refresh the row, not create a duplicate."""
    from app.ai.memory import episodic as ep

    sess = ChatSession(id=uuid.uuid4(), title="t")
    db.add(sess)
    await db.flush()

    with _patch_session(db):
        await ep._upsert_summary(sess.id, "v1", ["a"], "first")
        await ep._upsert_summary(sess.id, "v2", ["a", "b"], "second")

    rows = (await db.execute(select(SessionSummary))).scalars().all()
    assert len(rows) == 1
    assert rows[0].summary == "v2"
    assert rows[0].outcome == "second"
    assert rows[0].key_topics == ["a", "b"]
