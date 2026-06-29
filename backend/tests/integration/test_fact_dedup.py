"""Tests for LLM-driven fact dedup: update_user_fact + review add/replace routing."""

import json
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
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
    """Write path keeps an exact-text idempotency guard — a byte-identical
    re-save in the same turn collapses; semantic dedup is the reviewer's job."""
    from app.ai.memory import facts as memory_module
    from app.models.user_fact import UserFact

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
    from app.ai.memory import facts as memory_module
    from app.models.user_fact import UserFact

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
    from app.ai.memory import facts as memory_module
    from app.models.user_fact import UserFact

    row = UserFact(fact="Muốn tiết kiệm 50tr", category="goal", importance=7)
    db.add(row)
    await db.flush()

    expiry = datetime.now(UTC) + timedelta(days=30)
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
    from app.ai.memory import facts as memory_module
    from app.models.user_fact import UserFact

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


# ── load_existing_for_review covers the full active set ───────────────────


async def test_load_existing_for_review_returns_more_than_fifty(db: AsyncSession):
    """The reviewer must see ALL active facts, not just the freshest 50, or a
    duplicate older than the 50 most-recent rows would slip past dedup."""
    from app.ai.memory.fact_review import load_existing_for_review
    from app.models.user_fact import UserFact

    for i in range(60):
        db.add(UserFact(fact=f"fact {i}", category="general", importance=5))
    await db.flush()

    @asynccontextmanager
    async def _factory():
        yield db

    existing = await load_existing_for_review(_factory)
    assert len(existing) == 60


# ── _apply_review_item routing ────────────────────────────────────────────


async def test_apply_review_item_add(db: AsyncSession):
    from app.ai.memory import facts as memory_module
    from app.models.user_fact import UserFact

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
    from app.ai.memory import facts as memory_module
    from app.models.user_fact import UserFact

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
    from app.ai.memory import facts as memory_module
    from app.models.user_fact import UserFact

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
    from app.ai.memory import facts as memory_module
    from app.models.user_fact import UserFact

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
         patch("app.ai.memory.facts.client_factory", return_value=mock_client), \
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
    from app.ai.memory import facts as memory_module
    from app.models.user_fact import UserFact

    api_resp = MagicMock()
    api_resp.content = [MagicMock(text=json.dumps([
        {"fact": "Thích báo cáo tuần", "category": "preference", "importance": 6},
    ]))]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=api_resp)

    with _patch_session(db), \
         patch("app.ai.memory.facts.client_factory", return_value=mock_client), \
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


# ── Bi-temporal supersession ──────────────────────────────────────────────


async def test_supersede_retires_old_and_links_new(db: AsyncSession):
    """A value change keeps the old row (retired) and links the successor."""
    from app.ai.memory import facts as memory_module
    from app.models.user_fact import UserFact

    original = UserFact(fact="Thu nhập 15tr/tháng", category="context", importance=8)
    db.add(original)
    await db.flush()
    original_id = original.id

    with _patch_session(db):
        result = await memory_module.supersede_user_fact(
            old_fact_id=original_id,
            fact="Thu nhập 20tr/tháng (nâng từ 15tr)",
            category="context",
            importance=9,
            expires_at=None,
        )

    assert result["status"] == "superseded"
    rows = (await db.execute(select(UserFact))).scalars().all()
    assert len(rows) == 2  # old kept as history, not deleted
    old = next(r for r in rows if r.id == original_id)
    new = next(r for r in rows if r.id != original_id)
    assert old.superseded_at is not None
    assert new.superseded_at is None
    assert new.supersedes_id == original_id
    assert new.verified_by_user is False  # a changed value is unverified again


async def test_superseded_facts_drop_out_of_retrieval(db: AsyncSession):
    from app.ai.memory import facts as memory_module
    from app.models.user_fact import UserFact

    original = UserFact(fact="Thu nhập 15tr/tháng", category="context", importance=8)
    db.add(original)
    await db.flush()

    with _patch_session(db):
        await memory_module.supersede_user_fact(
            old_fact_id=original.id,
            fact="Thu nhập 20tr/tháng",
            category="context",
            importance=9,
            expires_at=None,
        )
        facts = await memory_module.get_user_facts(limit=20)

    surfaced = [f["fact"] for f in facts]
    assert surfaced == ["Thu nhập 20tr/tháng"]  # only the live value


async def test_build_facts_prompt_shows_previous_value(db: AsyncSession):
    from app.ai.memory import facts as memory_module
    from app.models.user_fact import UserFact

    original = UserFact(fact="Thu nhập 15tr/tháng", category="context", importance=8)
    db.add(original)
    await db.flush()

    with _patch_session(db):
        await memory_module.supersede_user_fact(
            old_fact_id=original.id,
            fact="Thu nhập 20tr/tháng",
            category="context",
            importance=9,
            expires_at=None,
        )
        prompt = await memory_module.build_facts_prompt(limit=20)

    assert "Thu nhập 20tr/tháng" in prompt
    assert "previously: Thu nhập 15tr/tháng" in prompt


async def test_supersede_missing_predecessor_is_skipped(db: AsyncSession):
    from app.ai.memory import facts as memory_module
    from app.models.user_fact import UserFact

    with _patch_session(db):
        result = await memory_module.supersede_user_fact(
            old_fact_id=uuid.uuid4(),  # no such row
            fact="anything",
            category="context",
            importance=5,
            expires_at=None,
        )

    assert result["status"] == "skipped"
    rows = (await db.execute(select(UserFact))).scalars().all()
    assert rows == []


async def test_apply_review_item_retire_drops_fact_without_replacement(db: AsyncSession):
    """'retire' stamps superseded_at with no successor — fact leaves retrieval."""
    from app.ai.memory import facts as memory_module
    from app.models.user_fact import UserFact

    row = UserFact(
        fact="Đang phân vân có nên cắt supplement", category="emotion", importance=6,
    )
    db.add(row)
    await db.flush()
    existing = [(row.id, row.fact)]

    with _patch_session(db):
        outcome = await memory_module._apply_review_item(
            {"action": "retire", "replaces": 1},
            existing=existing,
            session_id=uuid.uuid4(),
        )
        surfaced = await memory_module.get_user_facts(limit=20)

    assert outcome == "retired"
    rows = (await db.execute(select(UserFact))).scalars().all()
    assert len(rows) == 1  # row kept as history, not deleted
    assert rows[0].superseded_at is not None
    assert surfaced == []  # dropped from active retrieval


async def test_apply_review_item_retire_bad_index_skipped(db: AsyncSession):
    """A retire with an out-of-range index is a no-op, not a crash."""
    from app.ai.memory import facts as memory_module
    from app.models.user_fact import UserFact

    row = UserFact(fact="still true", category="general", importance=5)
    db.add(row)
    await db.flush()
    existing = [(row.id, row.fact)]

    with _patch_session(db):
        outcome = await memory_module._apply_review_item(
            {"action": "retire", "replaces": 99},
            existing=existing,
            session_id=uuid.uuid4(),
        )

    assert outcome == "skipped"
    rows = (await db.execute(select(UserFact))).scalars().all()
    assert rows[0].superseded_at is None  # untouched


async def test_apply_review_item_supersede_routes_to_history(db: AsyncSession):
    from app.ai.memory import facts as memory_module
    from app.models.user_fact import UserFact

    row = UserFact(fact="Mục tiêu tiết kiệm 50tr", category="goal", importance=7)
    db.add(row)
    await db.flush()
    existing = [(row.id, row.fact)]

    with _patch_session(db):
        outcome = await memory_module._apply_review_item(
            {"action": "supersede", "replaces": 1,
             "fact": "Mục tiêu tiết kiệm 120tr (nâng từ 50tr)",
             "category": "goal", "importance": 9},
            existing=existing,
            session_id=uuid.uuid4(),
        )

    assert outcome == "superseded"
    rows = (await db.execute(select(UserFact))).scalars().all()
    assert len(rows) == 2
    assert any(r.superseded_at is not None for r in rows)
    assert any("120tr" in r.fact and r.superseded_at is None for r in rows)
