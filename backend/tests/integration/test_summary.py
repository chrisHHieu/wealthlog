"""Tests for episodic memory (session summaries)."""

import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession


# ── Pure helpers ────────────────────────────────────────────────────────────


def test_relative_day_labels():
    from app.ai.memory.episodic import _relative_day

    now = datetime.now(timezone.utc)
    assert _relative_day(now) == "hôm nay"
    assert _relative_day(now - timedelta(days=1)) == "hôm qua"
    assert _relative_day(now - timedelta(days=3)) == "3 ngày trước"
    assert _relative_day(now - timedelta(days=10)) == "1 tuần trước"
    # 30+ days → date fallback
    long_ago = _relative_day(now - timedelta(days=45))
    assert "/" in long_ago


def test_extract_json_plain():
    from app.ai.memory.episodic import _extract_json

    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_markdown_wrapped():
    from app.ai.memory.episodic import _extract_json

    wrapped = '```json\n{"summary": "test", "key_topics": ["a"]}\n```'
    parsed = _extract_json(wrapped)
    assert parsed == {"summary": "test", "key_topics": ["a"]}


def test_extract_json_invalid_returns_none():
    from app.ai.memory.episodic import _extract_json

    assert _extract_json("not json") is None
    assert _extract_json('["an array, not an object"]') is None


def test_extract_json_deepseek_think_tags():
    """DeepSeek reasoning models wrap output in <think>...</think> before the JSON."""
    from app.ai.memory.episodic import _extract_json

    raw = (
        "<think>\nLet me analyze the conversation...\nSome reasoning here.\n</think>\n"
        '{"summary": "User wants to save money.", "key_topics": ["tiết kiệm"]}'
    )
    result = _extract_json(raw)
    assert result == {"summary": "User wants to save money.", "key_topics": ["tiết kiệm"]}


def test_extract_json_preamble_text():
    """Some models add 'Here is the JSON:' before the actual object."""
    from app.ai.memory.episodic import _extract_json

    raw = 'Here is the summary:\n{"summary": "test", "key_topics": []}'
    result = _extract_json(raw)
    assert result == {"summary": "test", "key_topics": []}


# ── summarize_session (fully mocked — no DB) ────────────────────────────────


async def test_summarize_session_no_api_key_returns_false():
    from app.ai.memory import episodic as summary_module

    with patch.object(summary_module, "settings") as s:
        s.anthropic_api_key = ""
        assert await summary_module.summarize_session(uuid.uuid4()) is False


async def test_summarize_session_too_few_messages():
    from app.ai.memory import episodic as summary_module

    with patch.object(summary_module, "settings") as s, \
         patch.object(summary_module, "_load_text_messages", AsyncMock(return_value=[])):
        s.anthropic_api_key = "key"
        assert await summary_module.summarize_session(uuid.uuid4()) is False


async def test_summarize_session_trailing_user_skipped():
    """If the conversation ends on a user message (interrupted), skip summarization."""
    from app.ai.memory import episodic as summary_module

    msgs = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "wait"},  # interrupted
    ]
    with patch.object(summary_module, "settings") as s, \
         patch.object(summary_module, "_load_text_messages", AsyncMock(return_value=msgs)):
        s.anthropic_api_key = "key"
        assert await summary_module.summarize_session(uuid.uuid4()) is False


async def test_summarize_session_happy_path_upserts():
    from app.ai.memory import episodic as summary_module

    msgs = [
        {"role": "user", "content": "Tôi muốn tiết kiệm 50tr mua xe"},
        {"role": "assistant", "content": "Lên kế hoạch 12 tháng được không?"},
    ]

    api_response = MagicMock()
    api_response.content = [MagicMock(text=json.dumps({
        "summary": "User hỏi kế hoạch tiết kiệm mua xe.",
        "key_topics": ["tiết kiệm", "mua xe"],
    }))]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=api_response)

    upsert_mock = AsyncMock()

    sid = uuid.uuid4()
    with patch.object(summary_module, "settings") as s, \
         patch.object(summary_module, "_load_text_messages", AsyncMock(return_value=msgs)), \
         patch.object(summary_module, "_upsert_summary", upsert_mock), \
         patch.object(summary_module.anthropic, "AsyncAnthropic", return_value=mock_client):
        s.anthropic_api_key = "key"
        s.session_summary_model = "claude-haiku-4-5-20251001"
        assert await summary_module.summarize_session(sid) is True

    upsert_mock.assert_awaited_once()
    called_sid, called_summary, called_topics = upsert_mock.await_args.args
    assert called_sid == sid
    assert "tiết kiệm" in called_summary.lower() or "mua xe" in called_summary.lower()
    assert called_topics == ["tiết kiệm", "mua xe"]


async def test_summarize_session_skips_empty_summary():
    from app.ai.memory import episodic as summary_module

    msgs = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    api_response = MagicMock()
    api_response.content = [MagicMock(text=json.dumps({
        "summary": "   ",
        "key_topics": [],
    }))]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=api_response)

    upsert_mock = AsyncMock()
    with patch.object(summary_module, "settings") as s, \
         patch.object(summary_module, "_load_text_messages", AsyncMock(return_value=msgs)), \
         patch.object(summary_module, "_upsert_summary", upsert_mock), \
         patch.object(summary_module.anthropic, "AsyncAnthropic", return_value=mock_client):
        s.anthropic_api_key = "key"
        s.session_summary_model = "claude-haiku-4-5-20251001"
        assert await summary_module.summarize_session(uuid.uuid4()) is False

    upsert_mock.assert_not_awaited()


async def test_summarize_session_tolerates_non_list_topics():
    """If the reviewer returns malformed key_topics, coerce to empty list."""
    from app.ai.memory import episodic as summary_module

    msgs = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]
    api_response = MagicMock()
    api_response.content = [MagicMock(text=json.dumps({
        "summary": "Phiên ngắn.",
        "key_topics": "not a list",
    }))]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=api_response)

    upsert_mock = AsyncMock()
    with patch.object(summary_module, "settings") as s, \
         patch.object(summary_module, "_load_text_messages", AsyncMock(return_value=msgs)), \
         patch.object(summary_module, "_upsert_summary", upsert_mock), \
         patch.object(summary_module.anthropic, "AsyncAnthropic", return_value=mock_client):
        s.anthropic_api_key = "key"
        s.session_summary_model = "claude-haiku-4-5-20251001"
        await summary_module.summarize_session(uuid.uuid4())

    _, _, topics = upsert_mock.await_args.args
    assert topics == []


# ── UserFact expiry filtering ───────────────────────────────────────────────


async def test_get_user_facts_filters_expired(db: AsyncSession):
    from contextlib import asynccontextmanager

    from app.models.user_fact import UserFact
    from app.ai.memory import facts as memory_module

    now = datetime.now(timezone.utc)
    db.add(UserFact(fact="evergreen", category="preference", expires_at=None))
    db.add(UserFact(fact="still valid", category="context",
                    expires_at=now + timedelta(days=1)))
    db.add(UserFact(fact="expired", category="context",
                    expires_at=now - timedelta(days=1)))
    await db.flush()

    @asynccontextmanager
    async def _patched():
        yield db

    with patch.object(memory_module, "get_session", _patched):
        facts = await memory_module.get_user_facts()

    texts = {f["fact"] for f in facts}
    assert "evergreen" in texts
    assert "still valid" in texts
    assert "expired" not in texts


# ── _compute_expiry ─────────────────────────────────────────────────────────


def test_compute_expiry_reviewer_explicit_days():
    from app.ai.memory.facts import _compute_expiry

    out = _compute_expiry({"expires_in_days": 30}, "context")
    assert out is not None
    assert (out - datetime.now(timezone.utc)).days in (29, 30)


def test_compute_expiry_context_default_fallback():
    from app.ai.memory import facts as memory_module

    with patch.object(memory_module, "settings") as s:
        s.user_fact_default_context_ttl_days = 45
        out = memory_module._compute_expiry({}, "context")

    assert out is not None
    assert (out - datetime.now(timezone.utc)).days in (44, 45)


def test_compute_expiry_evergreen_categories_return_none():
    from app.ai.memory.facts import _compute_expiry

    assert _compute_expiry({}, "preference") is None
    assert _compute_expiry({}, "habit") is None
    assert _compute_expiry({}, "goal") is None
    assert _compute_expiry({}, "general") is None


def test_compute_expiry_ignores_non_positive_days():
    from app.ai.memory.facts import _compute_expiry

    assert _compute_expiry({"expires_in_days": 0}, "preference") is None
    assert _compute_expiry({"expires_in_days": -5}, "preference") is None
    assert _compute_expiry({"expires_in_days": "not a number"}, "preference") is None
