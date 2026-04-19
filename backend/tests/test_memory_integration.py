"""Integration tests — verify memory layers work together end-to-end.

Tests the REAL flow:
1. Short-term: turn-boundary compaction preserves pair integrity + tool_use trace
2. Long-term:  user facts từ session A → inject vào system prompt session B
3. Background review: đủ turn → _run_review extract facts → facts có trong DB
"""

import json
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatMessage, ChatSession
from app.models.user_fact import UserFact


# ═══════════════════════════════════════════════════════════════════════════
# 1. SHORT-TERM MEMORY: turn-boundary compaction
# ═══════════════════════════════════════════════════════════════════════════


def _tool_turn(user_text: str, tool_id: str, tool_name: str,
               tool_input: dict, tool_result: str, final_text: str) -> list[dict]:
    """Build one full turn: user → assistant(tool_use) → tool_result → assistant(final)."""
    return [
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": tool_id, "name": tool_name, "input": tool_input},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": tool_id, "content": tool_result},
        ]},
        {"role": "assistant", "content": final_text},
    ]


def test_compact_history_passthrough_when_short():
    """≤ keep_recent_turns turns → no change."""
    from app.services.agent import _compact_history

    messages = (
        _tool_turn("Chi tháng 3?", "t1", "get_summary", {},
                   "Tổng: 8.5M", "Tháng 3 bạn chi 8.5M.")
        + _tool_turn("Còn tháng 2?", "t2", "get_summary", {"month": "2026-02"},
                     "Tổng: 7.2M", "Tháng 2 là 7.2M.")
    )

    result = _compact_history(messages, keep_recent_turns=3, old_tool_result_chars=100)
    assert result == messages


def test_compact_history_truncates_only_old_tool_results():
    """Old turns: tool_result bị cắt. Recent turns: nguyên vẹn."""
    from app.services.agent import _compact_history

    long_result = "X" * 2000  # far above max_chars
    short_result = "Budget còn dư 1M"

    messages = (
        _tool_turn("Q1", "t1", "get_a", {}, long_result, "A1")
        + _tool_turn("Q2", "t2", "get_b", {}, long_result, "A2")
        + _tool_turn("Q3", "t3", "get_c", {}, short_result, "A3")
        + _tool_turn("Q4", "t4", "get_d", {}, short_result, "A4")
    )

    result = _compact_history(messages, keep_recent_turns=2, old_tool_result_chars=100)

    def _find_result(tool_id: str) -> str:
        for msg in result:
            if msg["role"] != "user" or not isinstance(msg["content"], list):
                continue
            for b in msg["content"]:
                if isinstance(b, dict) and b.get("tool_use_id") == tool_id:
                    return b["content"]
        raise AssertionError(f"tool_use_id {tool_id} not found")

    # Old turns (t1, t2): truncated
    assert len(_find_result("t1")) < 2000
    assert "ký tự bị cắt" in _find_result("t1") or "cắt bớt" in _find_result("t1")
    assert len(_find_result("t2")) < 2000

    # Recent turns (t3, t4): untouched
    assert _find_result("t3") == short_result
    assert _find_result("t4") == short_result


def test_compact_history_preserves_tool_use_trace():
    """tool_use blocks in OLD turns stay verbatim — agent remembers what it called."""
    from app.services.agent import _compact_history

    messages = (
        _tool_turn("Q1", "t1", "get_spending_by_category",
                   {"month": "2026-01"}, "X" * 2000, "A1")
        + _tool_turn("Q2", "t2", "get_b", {}, "short", "A2")
        + _tool_turn("Q3", "t3", "get_c", {}, "short", "A3")
        + _tool_turn("Q4", "t4", "get_d", {}, "short", "A4")
    )

    result = _compact_history(messages, keep_recent_turns=2, old_tool_result_chars=100)

    # The old tool_use block must still carry name + input
    tool_use_blocks = [
        b for msg in result if isinstance(msg.get("content"), list)
        for b in msg["content"]
        if isinstance(b, dict) and b.get("type") == "tool_use"
    ]
    t1 = next((b for b in tool_use_blocks if b["id"] == "t1"), None)
    assert t1 is not None, "tool_use from old turn was dropped"
    assert t1["name"] == "get_spending_by_category"
    assert t1["input"] == {"month": "2026-01"}


def test_compact_history_never_splits_tool_use_pair():
    """Cut at assistant-final boundary — every tool_use has its tool_result in the same list."""
    from app.services.agent import _compact_history

    messages = (
        _tool_turn("Q1", "t1", "a", {}, "r1", "A1")
        + _tool_turn("Q2", "t2", "b", {}, "r2", "A2")
        + _tool_turn("Q3", "t3", "c", {}, "r3", "A3")
        + _tool_turn("Q4", "t4", "d", {}, "r4", "A4")
    )

    result = _compact_history(messages, keep_recent_turns=2, old_tool_result_chars=50)

    tool_use_ids = set()
    tool_result_ids = set()
    for msg in result:
        if not isinstance(msg.get("content"), list):
            continue
        for b in msg["content"]:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use":
                tool_use_ids.add(b["id"])
            elif b.get("type") == "tool_result":
                tool_result_ids.add(b["tool_use_id"])

    assert tool_use_ids == tool_result_ids, (
        f"Unpaired ids: use-only={tool_use_ids - tool_result_ids}, "
        f"result-only={tool_result_ids - tool_use_ids}"
    )


# ═══════════════════════════════════════════════════════════════════════════
# 3. LONG-TERM MEMORY: facts từ session A inject vào system prompt session B
# ═══════════════════════════════════════════════════════════════════════════


async def test_facts_from_session_a_appear_in_session_b_prompt(db: AsyncSession):
    """User facts saved in session A are injected into system prompt of session B."""
    from app.services.memory import build_facts_prompt, save_user_fact

    with _patch_get_session(db):
        # Session A: save some user facts (as if background review extracted them)
        session_a = str(uuid.uuid4())
        await save_user_fact("Lương 25 triệu/tháng", "context", session_a)
        await save_user_fact("Muốn mua xe trong 6 tháng", "goal", session_a)
        await save_user_fact("Hay quên ghi tiền mặt", "habit", session_a)

        # Session B: build system prompt — should include facts from session A
        facts_prompt = await build_facts_prompt()

    assert "[Thông tin đã biết về người dùng]" in facts_prompt
    assert "Lương 25 triệu/tháng" in facts_prompt
    assert "Muốn mua xe trong 6 tháng" in facts_prompt
    assert "Hay quên ghi tiền mặt" in facts_prompt
    assert "(Ngữ cảnh)" in facts_prompt
    assert "(Mục tiêu)" in facts_prompt
    assert "(Thói quen)" in facts_prompt


async def test_build_system_prompt_includes_user_facts(db: AsyncSession):
    """Full _build_system_prompt should contain the user facts section."""
    from app.services.agent import _build_system_prompt

    # Insert facts directly into DB
    db.add(UserFact(fact="Thu nhập 30 triệu", category="context"))
    db.add(UserFact(fact="Đầu tư chứng khoán", category="preference"))
    await db.flush()

    with _patch_get_session(db), \
         patch("app.services.agent.mcp") as mock_mcp:
        # Mock MCP resources to avoid real MCP calls
        mock_mcp.read_resource = AsyncMock(return_value=[])

        prompt = await _build_system_prompt()

    # System prompt should contain base + facts
    assert "WealthLog AI" in prompt
    assert "Thu nhập 30 triệu" in prompt
    assert "Đầu tư chứng khoán" in prompt
    assert "[Thông tin đã biết về người dùng]" in prompt


# ═══════════════════════════════════════════════════════════════════════════
# 4. BACKGROUND REVIEW: full flow qua session — extract & persist facts
# ═══════════════════════════════════════════════════════════════════════════


async def test_background_review_full_flow(db: AsyncSession):
    """Simulate a multi-turn conversation that triggers background review
    and verify facts are extracted and saved to DB."""
    from app.services.memory import _run_review

    session_id = uuid.uuid4()

    # Build a realistic conversation
    conversation = [
        {"role": "user", "content": "Tôi lương 20 triệu, trả lương ngày 15 hàng tháng"},
        {"role": "assistant", "content": "Ghi nhận! Lương 20 triệu, nhận ngày 15."},
        {"role": "user", "content": "Tôi muốn tiết kiệm 100 triệu để mua xe"},
        {"role": "assistant", "content": "Tôi sẽ giúp bạn lập kế hoạch tiết kiệm mua xe."},
        {"role": "user", "content": "Tôi hay quên ghi chi tiêu tiền mặt"},
        {"role": "assistant", "content": "Tôi sẽ nhắc nhở bạn ghi chép hàng ngày."},
    ]

    # Claude review response — simulating what Haiku would extract
    extracted_facts = [
        {"fact": "Lương 20 triệu/tháng, nhận ngày 15", "category": "context"},
        {"fact": "Mục tiêu tiết kiệm 100 triệu mua xe", "category": "goal"},
        {"fact": "Hay quên ghi chi tiêu tiền mặt", "category": "habit"},
    ]

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps(extracted_facts))]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with _patch_get_session(db), \
         patch("app.services.memory.anthropic.AsyncAnthropic", return_value=mock_client), \
         patch("app.services.memory.settings") as mock_settings:
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.agent_review_model = "claude-haiku-4-5-20251001"

        # Run review directly (simulating what maybe_trigger_review dispatches)
        await _run_review(session_id, conversation)

    # Verify all 3 facts are in the DB
    rows = (await db.execute(select(UserFact))).scalars().all()
    saved = {r.fact: r.category for r in rows}

    assert "Lương 20 triệu/tháng, nhận ngày 15" in saved
    assert saved["Lương 20 triệu/tháng, nhận ngày 15"] == "context"

    assert "Mục tiêu tiết kiệm 100 triệu mua xe" in saved
    assert saved["Mục tiêu tiết kiệm 100 triệu mua xe"] == "goal"

    assert "Hay quên ghi chi tiêu tiền mặt" in saved
    assert saved["Hay quên ghi chi tiêu tiền mặt"] == "habit"


async def test_background_review_across_sessions(db: AsyncSession):
    """Facts from session 1's review should NOT be duplicated when session 2 runs review."""
    from app.services.memory import _run_review

    # --- Session 1: extract initial facts ---
    sid1 = uuid.uuid4()
    conv1 = [
        {"role": "user", "content": "Tôi là freelancer, thu nhập không ổn định"},
        {"role": "assistant", "content": "Ghi nhận, tôi sẽ lưu ý điều này."},
    ]

    response1 = MagicMock()
    response1.content = [MagicMock(text=json.dumps([
        {"fact": "Freelancer, thu nhập không ổn định", "category": "context"},
    ]))]

    mock_client1 = AsyncMock()
    mock_client1.messages.create = AsyncMock(return_value=response1)

    with _patch_get_session(db), \
         patch("app.services.memory.anthropic.AsyncAnthropic", return_value=mock_client1), \
         patch("app.services.memory.settings") as s:
        s.anthropic_api_key = "key"
        s.agent_review_model = "claude-haiku-4-5-20251001"
        await _run_review(sid1, conv1)

    rows_after_s1 = (await db.execute(select(UserFact))).scalars().all()
    assert len(rows_after_s1) == 1

    # --- Session 2: same fact + a new one ---
    sid2 = uuid.uuid4()
    conv2 = [
        {"role": "user", "content": "Thu nhập tháng này 15 triệu, ít hơn bình thường"},
        {"role": "assistant", "content": "Tôi thấy bạn là freelancer nên thu nhập hay biến động."},
    ]

    response2 = MagicMock()
    response2.content = [MagicMock(text=json.dumps([
        {"fact": "Freelancer, thu nhập không ổn định", "category": "context"},  # duplicate
        {"fact": "Thu nhập trung bình khoảng 15-20 triệu", "category": "context"},  # new
    ]))]

    mock_client2 = AsyncMock()
    mock_client2.messages.create = AsyncMock(return_value=response2)

    with _patch_get_session(db), \
         patch("app.services.memory.anthropic.AsyncAnthropic", return_value=mock_client2), \
         patch("app.services.memory.settings") as s:
        s.anthropic_api_key = "key"
        s.agent_review_model = "claude-haiku-4-5-20251001"
        await _run_review(sid2, conv2)

    rows_after_s2 = (await db.execute(select(UserFact))).scalars().all()

    # Should be 2 facts total, NOT 3 (duplicate skipped)
    assert len(rows_after_s2) == 2
    facts = {r.fact for r in rows_after_s2}
    assert "Freelancer, thu nhập không ổn định" in facts
    assert "Thu nhập trung bình khoảng 15-20 triệu" in facts


async def test_review_cadence_fires_on_db_turn_count(db: AsyncSession):
    """Cadence is driven by DB count of user turns — survives process restart.

    Inserts real ChatMessage rows; maybe_trigger_review counts them and only
    fires when count is a positive multiple of cadence.
    """
    from app.services.memory import build_facts_prompt, maybe_trigger_review

    session = ChatSession(title="Cadence test")
    db.add(session)
    await db.flush()

    review_task = None

    def capture_task(coro):
        nonlocal review_task
        review_task = coro
        return MagicMock()

    async def _trigger_with_n_user_turns(n: int) -> None:
        nonlocal review_task
        review_task = None
        await db.execute(
            ChatMessage.__table__.delete().where(
                ChatMessage.session_id == session.id,
            )
        )
        for i in range(n):
            db.add(ChatMessage(
                session_id=session.id, role="user", content=f"turn {i}",
            ))
        await db.flush()

        with _patch_get_session(db), \
             patch("app.services.memory.settings") as s, \
             patch("app.services.memory.asyncio.create_task", side_effect=capture_task):
            s.agent_review_cadence = 3
            await maybe_trigger_review(session.id, messages=[])

    # Count=2 → skip (2 % 3 != 0)
    await _trigger_with_n_user_turns(2)
    assert review_task is None

    # Count=3 → fire
    await _trigger_with_n_user_turns(3)
    assert review_task is not None

    # Count=6 → fire again
    await _trigger_with_n_user_turns(6)
    assert review_task is not None

    # Drain the coroutine so it doesn't emit warnings
    review_task.close()


async def test_review_cadence_skips_empty_user_rows(db: AsyncSession):
    """Empty-content user rows (tool_result plumbing) don't count as turns."""
    from app.services.memory import maybe_trigger_review

    session = ChatSession(title="Cadence — empty rows")
    db.add(session)
    await db.flush()

    # 2 real user turns + 5 empty (tool_result) rows → only the 2 should count
    db.add(ChatMessage(session_id=session.id, role="user", content="Q1"))
    db.add(ChatMessage(session_id=session.id, role="user", content="Q2"))
    for _ in range(5):
        db.add(ChatMessage(session_id=session.id, role="user", content=""))
    await db.flush()

    review_task = None

    def capture_task(coro):
        nonlocal review_task
        review_task = coro
        return MagicMock()

    with _patch_get_session(db), \
         patch("app.services.memory.settings") as s, \
         patch("app.services.memory.asyncio.create_task", side_effect=capture_task):
        s.agent_review_cadence = 3
        await maybe_trigger_review(session.id, messages=[])

    # real turn count = 2, not 7 → should NOT fire
    assert review_task is None


# ═══════════════════════════════════════════════════════════════════════════
# 5. SESSION PERSISTENCE: messages saved & reloaded across requests
# ═══════════════════════════════════════════════════════════════════════════


async def test_messages_persist_and_reload(db: AsyncSession):
    """Messages saved to a session can be fully reloaded."""
    from sqlalchemy.orm import selectinload

    # Create session
    session = ChatSession(title="Persistence test")
    db.add(session)
    await db.flush()
    sid = session.id

    # Simulate multi-turn conversation being saved
    turns = [
        ("user", "Chi tiêu tháng này bao nhiêu?"),
        ("assistant", "Tổng chi tháng 3: 8,500,000 VND"),
        ("user", "So sánh với tháng trước?"),
        ("assistant", "Tháng 2: 7,200,000 — tăng 18% so với tháng trước."),
        ("user", "Khoản nào tăng nhiều nhất?"),
        ("assistant", "Ăn uống tăng 500,000 (+25%), di chuyển tăng 300,000 (+40%)."),
    ]

    for role, content in turns:
        db.add(ChatMessage(session_id=sid, role=role, content=content))
    await db.flush()

    # Reload session with messages (simulating GET /chat/sessions/{id})
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == sid)
    )
    loaded = result.scalar_one()

    assert loaded.title == "Persistence test"
    assert len(loaded.messages) == 6

    # Verify order and content
    for i, (expected_role, expected_content) in enumerate(turns):
        assert loaded.messages[i].role == expected_role
        assert loaded.messages[i].content == expected_content


async def test_multiple_sessions_isolated(db: AsyncSession):
    """Messages from different sessions don't leak into each other."""
    s1 = ChatSession(title="Session 1")
    s2 = ChatSession(title="Session 2")
    db.add_all([s1, s2])
    await db.flush()

    db.add(ChatMessage(session_id=s1.id, role="user", content="Msg in S1"))
    db.add(ChatMessage(session_id=s2.id, role="user", content="Msg in S2"))
    await db.flush()

    # Load S1 messages
    from sqlalchemy.orm import selectinload
    r1 = await db.execute(
        select(ChatSession).options(selectinload(ChatSession.messages))
        .where(ChatSession.id == s1.id)
    )
    loaded1 = r1.scalar_one()
    assert len(loaded1.messages) == 1
    assert loaded1.messages[0].content == "Msg in S1"

    # Load S2 messages
    r2 = await db.execute(
        select(ChatSession).options(selectinload(ChatSession.messages))
        .where(ChatSession.id == s2.id)
    )
    loaded2 = r2.scalar_one()
    assert len(loaded2.messages) == 1
    assert loaded2.messages[0].content == "Msg in S2"


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


def _patch_get_session(db: AsyncSession):
    """Redirect standalone get_session() calls to the test transaction."""

    @asynccontextmanager
    async def _mock():
        yield db

    return patch("app.services.memory.get_session", _mock)
