"""Tests for long-term memory (user facts) and background review agent."""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession
from app.models.user_fact import UserFact


# ── User Facts API (CRUD) ──────────────────────────────────────────────────


async def test_list_facts_empty(client: AsyncClient):
    r = await client.get("/api/memory/facts")
    assert r.status_code == 200
    assert r.json() == []


async def test_create_fact(client: AsyncClient):
    r = await client.post("/api/memory/facts", json={
        "fact": "Lương ngày 15 hàng tháng",
        "category": "context",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["fact"] == "Lương ngày 15 hàng tháng"
    assert data["category"] == "context"
    assert "id" in data


async def test_create_fact_default_category(client: AsyncClient):
    r = await client.post("/api/memory/facts", json={"fact": "Some fact"})
    assert r.status_code == 200
    assert r.json()["category"] == "general"


async def test_list_facts_returns_created(client: AsyncClient):
    await client.post("/api/memory/facts", json={"fact": "Fact A", "category": "habit"})
    await client.post("/api/memory/facts", json={"fact": "Fact B", "category": "goal"})
    r = await client.get("/api/memory/facts")
    assert r.status_code == 200
    facts = r.json()
    assert len(facts) >= 2
    fact_texts = [f["fact"] for f in facts]
    assert "Fact A" in fact_texts
    assert "Fact B" in fact_texts


async def test_delete_fact(client: AsyncClient):
    created = (await client.post("/api/memory/facts", json={"fact": "To delete"})).json()
    r = await client.delete(f"/api/memory/facts/{created['id']}")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    # Verify gone from list
    r2 = await client.get("/api/memory/facts")
    ids = [f["id"] for f in r2.json()]
    assert created["id"] not in ids


async def test_delete_fact_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    r = await client.delete(f"/api/memory/facts/{fake_id}")
    assert r.status_code == 404


# ── Memory Service: save_user_fact (dedup) ──────────────────────────────────


async def test_save_user_fact_new(db: AsyncSession):
    """save_user_fact stores a new fact and returns status='saved'."""
    from app.ai.memory.facts import save_user_fact

    # Patch get_session to use the test db
    with _patch_get_session(db):
        result = await save_user_fact("Thích uống cà phê buổi sáng", "preference")

    assert result["status"] == "saved"
    assert result["category"] == "preference"


async def test_save_user_fact_duplicate(db: AsyncSession):
    """Exact duplicate facts are detected and skipped."""
    from app.ai.memory.facts import save_user_fact

    fact_text = "Trả lương ngày 25"
    with _patch_get_session(db):
        r1 = await save_user_fact(fact_text, "context")
        r2 = await save_user_fact(fact_text, "context")

    assert r1["status"] == "saved"
    assert r2["status"] == "duplicate"


# ── Memory Service: build_facts_prompt ──────────────────────────────────────


async def test_build_facts_prompt_empty(db: AsyncSession):
    """Returns empty string when no facts exist."""
    from app.ai.memory.facts import build_facts_prompt

    with _patch_get_session(db):
        result = await build_facts_prompt()

    assert result == ""


async def test_build_facts_prompt_with_facts(db: AsyncSession):
    """Returns formatted prompt block with all facts."""
    from app.ai.memory.facts import build_facts_prompt

    db.add(UserFact(fact="Lương 20 triệu/tháng", category="context"))
    db.add(UserFact(fact="Muốn tiết kiệm 100 triệu", category="goal"))
    await db.flush()

    with _patch_get_session(db):
        result = await build_facts_prompt()

    assert "[Thông tin đã biết về người dùng]" in result
    assert "Lương 20 triệu/tháng" in result
    assert "Muốn tiết kiệm 100 triệu" in result
    assert "(Mục tiêu)" in result
    assert "(Ngữ cảnh)" in result
    assert "[Hết thông tin người dùng]" in result


# ── Memory Service: maybe_trigger_review ────────────────────────────────────


async def test_maybe_trigger_review_cadence(db: AsyncSession):
    """Review fires only when DB user-turn count is a positive multiple of cadence."""
    from contextlib import asynccontextmanager

    from app.ai.memory.facts import maybe_trigger_review

    session = ChatSession(title="cadence test")
    db.add(session)
    await db.flush()

    @asynccontextmanager
    async def _patched_session():
        yield db

    async def _fire_after_n_turns(n: int) -> bool:
        await db.execute(
            ChatMessage.__table__.delete().where(
                ChatMessage.session_id == session.id,
            )
        )
        for i in range(n):
            db.add(ChatMessage(
                session_id=session.id, role="user", content=f"msg {i}",
            ))
        await db.flush()

        with patch("app.ai.memory.facts.get_session", _patched_session), \
             patch("app.ai.memory.facts.settings") as s, \
             patch("app.ai.memory.facts.asyncio") as mock_asyncio:
            s.agent_review_cadence = 3
            await maybe_trigger_review(session.id, [{"role": "user", "content": "x"}])
            return mock_asyncio.create_task.called

    assert await _fire_after_n_turns(2) is False
    assert await _fire_after_n_turns(3) is True
    assert await _fire_after_n_turns(5) is False
    assert await _fire_after_n_turns(6) is True


# ── Background Review Agent (_run_review) ───────────────────────────────────


async def test_run_review_extracts_and_saves_facts(db: AsyncSession):
    """_run_review should call Claude and save extracted facts."""
    from app.ai.memory.facts import _run_review

    sid = uuid.uuid4()
    messages = [
        {"role": "user", "content": "Tôi lương 20 triệu, muốn tiết kiệm mua nhà"},
        {"role": "assistant", "content": "Tôi sẽ giúp bạn lập kế hoạch tiết kiệm."},
    ]

    # Mock Claude response with extracted facts
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps([
        {"fact": "Lương 20 triệu/tháng", "category": "context"},
        {"fact": "Muốn tiết kiệm mua nhà", "category": "goal"},
    ]))]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with _patch_get_session(db), \
         patch("app.ai.memory.facts.anthropic.AsyncAnthropic", return_value=mock_client), \
         patch("app.ai.memory.facts.settings") as mock_settings:
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.agent_review_model = "claude-haiku-4-5-20251001"

        await _run_review(sid, messages)

    # Verify facts were saved
    rows = (await db.execute(select(UserFact))).scalars().all()
    saved_facts = [r.fact for r in rows]
    assert "Lương 20 triệu/tháng" in saved_facts
    assert "Muốn tiết kiệm mua nhà" in saved_facts


async def test_run_review_skips_existing_facts(db: AsyncSession):
    """_run_review should not duplicate facts that already exist."""
    from app.ai.memory.facts import _run_review

    # Pre-insert an existing fact
    db.add(UserFact(fact="Lương 20 triệu/tháng", category="context"))
    await db.flush()

    sid = uuid.uuid4()
    messages = [
        {"role": "user", "content": "Lương tôi 20 triệu"},
        {"role": "assistant", "content": "Noted."},
    ]

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps([
        {"fact": "Lương 20 triệu/tháng", "category": "context"},  # duplicate
        {"fact": "Thích xem báo cáo tuần", "category": "preference"},  # new
    ]))]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with _patch_get_session(db), \
         patch("app.ai.memory.facts.anthropic.AsyncAnthropic", return_value=mock_client), \
         patch("app.ai.memory.facts.settings") as mock_settings:
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.agent_review_model = "claude-haiku-4-5-20251001"

        await _run_review(sid, messages)

    rows = (await db.execute(select(UserFact))).scalars().all()
    facts = [r.fact for r in rows]
    assert facts.count("Lương 20 triệu/tháng") == 1  # no duplicate
    assert "Thích xem báo cáo tuần" in facts


async def test_run_review_handles_empty_response(db: AsyncSession):
    """_run_review handles Claude returning empty array gracefully."""
    from app.ai.memory.facts import _run_review

    sid = uuid.uuid4()
    messages = [{"role": "user", "content": "Xin chào"}, {"role": "assistant", "content": "Chào!"}]

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="[]")]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with _patch_get_session(db), \
         patch("app.ai.memory.facts.anthropic.AsyncAnthropic", return_value=mock_client), \
         patch("app.ai.memory.facts.settings") as mock_settings:
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.agent_review_model = "claude-haiku-4-5-20251001"

        await _run_review(sid, messages)  # should not raise

    rows = (await db.execute(select(UserFact))).scalars().all()
    assert len(rows) == 0


async def test_run_review_handles_markdown_wrapped_json(db: AsyncSession):
    """Claude sometimes wraps JSON in ```json ... ``` — we should handle it."""
    from app.ai.memory.facts import _run_review

    sid = uuid.uuid4()
    messages = [
        {"role": "user", "content": "Tôi là sinh viên"},
        {"role": "assistant", "content": "Ghi nhận."},
    ]

    wrapped_json = '```json\n[{"fact": "Là sinh viên", "category": "context"}]\n```'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=wrapped_json)]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with _patch_get_session(db), \
         patch("app.ai.memory.facts.anthropic.AsyncAnthropic", return_value=mock_client), \
         patch("app.ai.memory.facts.settings") as mock_settings:
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.agent_review_model = "claude-haiku-4-5-20251001"

        await _run_review(sid, messages)

    rows = (await db.execute(select(UserFact))).scalars().all()
    assert any(r.fact == "Là sinh viên" for r in rows)


async def test_run_review_invalid_category_defaults_to_general(db: AsyncSession):
    """Unknown categories should fallback to 'general'."""
    from app.ai.memory.facts import _run_review

    sid = uuid.uuid4()
    messages = [
        {"role": "user", "content": "test"},
        {"role": "assistant", "content": "ok"},
    ]

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps([
        {"fact": "Some fact", "category": "unknown_cat"},
    ]))]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with _patch_get_session(db), \
         patch("app.ai.memory.facts.anthropic.AsyncAnthropic", return_value=mock_client), \
         patch("app.ai.memory.facts.settings") as mock_settings:
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.agent_review_model = "claude-haiku-4-5-20251001"

        await _run_review(sid, messages)

    rows = (await db.execute(select(UserFact))).scalars().all()
    assert len(rows) == 1
    assert rows[0].category == "general"


async def test_run_review_no_api_key_skips():
    """_run_review should exit silently when no API key is configured."""
    from app.ai.memory.facts import _run_review

    sid = uuid.uuid4()
    messages = [{"role": "user", "content": "test"}]

    with patch("app.ai.memory.facts.settings") as mock_settings:
        mock_settings.anthropic_api_key = ""
        await _run_review(sid, messages)  # should return immediately, no error


# ── Helpers ─────────────────────────────────────────────────────────────────


def _patch_get_session(db: AsyncSession):
    """Patch app.ai.memory.facts.get_session to use test DB.

    Returns a context manager that redirects standalone session calls
    to the test transaction, so changes are visible and rolled back after test.
    """
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _mock_get_session():
        yield db

    return patch("app.ai.memory.facts.get_session", _mock_get_session)
