"""Tests for LLM-driven fact dedup: update_user_fact + review add/replace routing."""

import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _patch_session(db: AsyncSession):
    from app.ai.memory import facts as memory_module

    @asynccontextmanager
    async def _patched():
        yield db

    return patch.object(memory_module, "get_session", _patched)


# ── save_user_fact dedup (SQLite exact-match path) ────────────────────────


async def test_save_user_fact_rejects_exact_duplicate(db: AsyncSession):
    """SQLite has no pg_trgm; the dispatcher must keep exact-equality dedup."""
    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

    with _patch_session(db):
        first = await memory_module.save_user_fact(
            fact="Tiết kiệm 50tr để mua xe", category="goal", importance=8,
        )
        second = await memory_module.save_user_fact(
            fact="Tiết kiệm 50tr để mua xe", category="goal", importance=8,
        )

    assert first["status"] == "saved"
    assert second["status"] == "duplicate"
    rows = (await db.execute(select(UserFact))).scalars().all()
    assert len(rows) == 1


async def test_save_user_fact_distinct_facts_both_save(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

    with _patch_session(db):
        await memory_module.save_user_fact(
            fact="Lương trả vào ngày 15", category="habit", importance=6,
        )
        await memory_module.save_user_fact(
            fact="Có 2 con nhỏ", category="context", importance=7,
        )

    rows = (await db.execute(select(UserFact))).scalars().all()
    assert len(rows) == 2


# ── update_user_fact ───────────────────────────────────────────────────────


async def test_update_user_fact_applies_all_fields(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

    row = UserFact(fact="Muốn tiết kiệm 50tr", category="goal", importance=7)
    db.add(row)
    await db.flush()

    expiry = datetime.now(timezone.utc) + timedelta(days=30)
    with _patch_session(db):
        ok = await memory_module.update_user_fact(
            fact_id=row.id,
            fact="Muốn tiết kiệm 80tr (nâng từ 50tr)",
            category="goal",
            importance=9,
            expires_at=expiry,
        )

    assert ok is True
    refreshed = (await db.execute(select(UserFact))).scalar_one()
    assert refreshed.fact == "Muốn tiết kiệm 80tr (nâng từ 50tr)"
    assert refreshed.importance == 9
    assert refreshed.expires_at is not None


async def test_update_user_fact_preserves_identity_and_stats(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

    original_id = uuid.uuid4()
    row = UserFact(
        id=original_id,
        fact="old text",
        category="general",
        importance=5,
        access_count=7,
    )
    db.add(row)
    await db.flush()
    original_created_at = row.created_at

    with _patch_session(db):
        await memory_module.update_user_fact(
            fact_id=original_id,
            fact="new text",
            category="general",
            importance=5,
            expires_at=None,
        )

    refreshed = (await db.execute(select(UserFact))).scalar_one()
    assert refreshed.id == original_id
    assert refreshed.access_count == 7  # preserved
    assert refreshed.created_at == original_created_at  # preserved


async def test_update_user_fact_missing_returns_false(db: AsyncSession):
    from app.ai.memory import facts as memory_module

    with _patch_session(db):
        ok = await memory_module.update_user_fact(
            fact_id=uuid.uuid4(),
            fact="ghost",
            category="general",
            importance=5,
            expires_at=None,
        )
    assert ok is False


# ── _apply_review_item routing ────────────────────────────────────────────


async def test_apply_review_item_add(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

    with _patch_session(db):
        outcome = await memory_module._apply_review_item(
            {"action": "add", "fact": "Có 2 con nhỏ",
             "category": "context", "importance": 7},
            existing=[],
            session_id=uuid.uuid4(),
        )

    assert outcome == "saved"
    rows = (await db.execute(select(UserFact))).scalars().all()
    assert len(rows) == 1 and rows[0].fact == "Có 2 con nhỏ"


async def test_apply_review_item_replace_updates_existing(db: AsyncSession):
    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

    row = UserFact(fact="Mục tiêu 50tr", category="goal", importance=7)
    db.add(row)
    await db.flush()
    existing = [(row.id, row.fact)]

    with _patch_session(db):
        outcome = await memory_module._apply_review_item(
            {"action": "replace", "replaces": 1,
             "fact": "Mục tiêu 80tr (nâng từ 50tr)",
             "category": "goal", "importance": 9},
            existing=existing,
            session_id=uuid.uuid4(),
        )

    assert outcome == "updated"
    rows = (await db.execute(select(UserFact))).scalars().all()
    assert len(rows) == 1  # in-place update, not net-new
    assert rows[0].fact == "Mục tiêu 80tr (nâng từ 50tr)"
    assert rows[0].importance == 9


async def test_apply_review_item_replace_with_bad_index_falls_back_to_add(db: AsyncSession):
    """A bogus 'replaces' index shouldn't drop the insight — treat as add."""
    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

    row = UserFact(fact="existing", category="general", importance=5)
    db.add(row)
    await db.flush()
    existing = [(row.id, row.fact)]

    with _patch_session(db):
        outcome = await memory_module._apply_review_item(
            {"action": "replace", "replaces": 99,  # out of range
             "fact": "salvaged insight", "category": "general", "importance": 5},
            existing=existing,
            session_id=uuid.uuid4(),
        )

    assert outcome == "saved"
    rows = (await db.execute(select(UserFact))).scalars().all()
    texts = {r.fact for r in rows}
    assert "existing" in texts
    assert "salvaged insight" in texts


async def test_apply_review_item_empty_fact_skipped(db: AsyncSession):
    from app.ai.memory import facts as memory_module

    with _patch_session(db):
        outcome = await memory_module._apply_review_item(
            {"action": "add", "fact": "   "},
            existing=[],
            session_id=uuid.uuid4(),
        )

    assert outcome == "skipped"


# ── End-to-end _run_review with add+replace ───────────────────────────────


async def test_run_review_routes_add_and_replace(db: AsyncSession):
    """Mixed batch: one add + one replace against an existing fact."""
    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

    original = UserFact(fact="Mục tiêu tiết kiệm 50tr", category="goal", importance=7)
    db.add(original)
    await db.flush()
    original_id = original.id

    api_resp = MagicMock()
    api_resp.content = [MagicMock(text=json.dumps([
        {"action": "replace", "replaces": 1,
         "fact": "Mục tiêu tiết kiệm 80tr (nâng từ 50tr)",
         "category": "goal", "importance": 9},
        {"action": "add", "fact": "Có 2 con nhỏ",
         "category": "context", "importance": 7},
    ]))]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=api_resp)

    with _patch_session(db), \
         patch("app.ai.memory.facts.anthropic.AsyncAnthropic", return_value=mock_client), \
         patch("app.ai.memory.facts.settings") as s:
        s.anthropic_api_key = "key"
        s.agent_review_model = "claude-haiku-4-5-20251001"
        s.user_fact_default_context_ttl_days = 90

        await memory_module._run_review(uuid.uuid4(), [
            {"role": "user", "content": "Tôi muốn nâng mục tiêu lên 80tr"},
            {"role": "assistant", "content": "OK"},
        ])

    rows = (await db.execute(select(UserFact))).scalars().all()
    assert len(rows) == 2  # replace is in-place, not new
    by_id = {r.id: r for r in rows}
    assert "80tr" in by_id[original_id].fact
    assert by_id[original_id].importance == 9
    new = [r for r in rows if r.id != original_id][0]
    assert new.fact == "Có 2 con nhỏ"


async def test_run_review_replace_missing_action_defaults_to_add(db: AsyncSession):
    """Items without an 'action' key are treated as add (backward compat)."""
    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

    api_resp = MagicMock()
    api_resp.content = [MagicMock(text=json.dumps([
        {"fact": "Thích báo cáo tuần", "category": "preference", "importance": 6},
    ]))]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=api_resp)

    with _patch_session(db), \
         patch("app.ai.memory.facts.anthropic.AsyncAnthropic", return_value=mock_client), \
         patch("app.ai.memory.facts.settings") as s:
        s.anthropic_api_key = "key"
        s.agent_review_model = "claude-haiku-4-5-20251001"
        s.user_fact_default_context_ttl_days = 90

        await memory_module._run_review(uuid.uuid4(), [
            {"role": "user", "content": "Tôi thích xem báo cáo tuần"},
            {"role": "assistant", "content": "OK"},
        ])

    rows = (await db.execute(select(UserFact))).scalars().all()
    assert len(rows) == 1
    assert rows[0].fact == "Thích báo cáo tuần"
