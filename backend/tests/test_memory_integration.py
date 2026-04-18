"""Integration tests — verify memory layers work together end-to-end.

Tests the REAL flow:
1. Short-term: long conversation → _compress_history tóm tắt tin cũ
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
# 1. SHORT-TERM MEMORY: _compress_history tóm tắt khi vượt token budget
# ═══════════════════════════════════════════════════════════════════════════


def _make_conversation(n_pairs: int) -> list[dict]:
    """Build a conversation with n user/assistant pairs."""
    msgs = []
    for i in range(n_pairs):
        msgs.append({"role": "user", "content": f"Tin nhắn user lần {i + 1}: chi tiêu tháng này"})
        msgs.append({"role": "assistant", "content": f"Trả lời assistant lần {i + 1}: tổng chi 5 triệu"})
    return msgs


async def test_compress_history_triggers_when_over_budget():
    """When token count exceeds budget, old messages are replaced by summary."""
    from app.services.agent import _compress_history

    messages = _make_conversation(10)  # 20 messages total
    assert len(messages) == 20

    # Mock client.messages.count_tokens to return a high token count
    mock_client = AsyncMock()
    call_count = 0

    async def _fake_count_tokens(**kwargs):
        nonlocal call_count
        call_count += 1
        n = len(kwargs.get("messages", []))
        if call_count == 1:
            # First call: original messages → over budget
            return MagicMock(input_tokens=20000)
        # Second call: compressed → under budget
        return MagicMock(input_tokens=3000)

    mock_client.messages.count_tokens = AsyncMock(side_effect=_fake_count_tokens)

    result = await _compress_history(
        client=mock_client,
        messages=messages,
        max_tokens=10000,  # budget
        keep_recent=6,
    )

    # Should be compressed: fewer messages than original
    assert len(result) < len(messages)

    # First message should be the summary block
    assert "[Tóm tắt cuộc trò chuyện trước đó]" in result[0]["content"]
    assert result[0]["role"] == "user"

    # Summary should contain snippets of old messages
    summary = result[0]["content"]
    assert "User:" in summary
    assert "AI:" in summary

    # Recent 6 messages should be preserved intact
    original_recent = messages[-6:]
    # Find them in result (may have a filler assistant message before them)
    for orig in original_recent:
        assert any(
            m["content"] == orig["content"] for m in result
        ), f"Recent message lost: {orig['content'][:50]}"

    # Should end with summary marker
    assert "[Hết tóm tắt — cuộc trò chuyện tiếp tục bên dưới]" in summary


async def test_compress_history_keeps_all_when_under_budget():
    """When under token budget, messages are returned unchanged."""
    from app.services.agent import _compress_history

    messages = _make_conversation(5)  # 10 messages

    mock_client = AsyncMock()
    mock_client.messages.count_tokens = AsyncMock(
        return_value=MagicMock(input_tokens=3000),  # well under budget
    )

    result = await _compress_history(
        client=mock_client,
        messages=messages,
        max_tokens=10000,
        keep_recent=6,
    )

    # No compression needed — same messages returned
    assert len(result) == len(messages)
    assert result == messages


async def test_compress_history_skips_when_few_messages():
    """When total messages <= keep_recent, skip entirely (no API call)."""
    from app.services.agent import _compress_history

    messages = _make_conversation(2)  # 4 messages, keep_recent=6

    mock_client = AsyncMock()
    mock_client.messages.count_tokens = AsyncMock()

    result = await _compress_history(
        client=mock_client,
        messages=messages,
        max_tokens=10000,
        keep_recent=6,
    )

    assert result == messages
    # Should NOT call count_tokens at all
    mock_client.messages.count_tokens.assert_not_called()


async def test_compress_ensures_valid_alternation():
    """After compression, user/assistant alternation must be valid for Claude API."""
    from app.services.agent import _compress_history

    messages = _make_conversation(8)  # 16 messages

    mock_client = AsyncMock()
    call_count = 0

    async def _fake(**kwargs):
        nonlocal call_count
        call_count += 1
        return MagicMock(input_tokens=20000 if call_count == 1 else 3000)

    mock_client.messages.count_tokens = AsyncMock(side_effect=_fake)

    result = await _compress_history(
        client=mock_client,
        messages=messages,
        max_tokens=5000,
        keep_recent=6,
    )

    # Verify alternation: user, assistant, user, assistant, ...
    for i in range(len(result) - 1):
        if result[i]["role"] == "user":
            assert result[i + 1]["role"] == "assistant", (
                f"Expected assistant after user at index {i}, got {result[i + 1]['role']}"
            )


# ═══════════════════════════════════════════════════════════════════════════
# 2. COMPACT OLD TOOL RESULTS (agent loop nội bộ)
# ═══════════════════════════════════════════════════════════════════════════


async def test_compact_old_tool_results_keeps_recent():
    """Tool results from recent iterations preserved, old ones compacted."""
    from app.services.agent import _compact_old_tool_results

    messages = [
        {"role": "user", "content": "Tổng chi tháng này"},
        # Iteration 1 - assistant calls tool
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": "t1", "name": "get_summary", "input": {}},
        ]},
        # Iteration 1 - tool result (OLD → should be compacted)
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t1",
             "content": "Chi tiêu tháng 3: Ăn uống 2,000,000 | Di chuyển 500,000 | ..."},
        ]},
        # Iteration 2 - assistant calls another tool
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": "t2", "name": "get_budget", "input": {}},
        ]},
        # Iteration 2 - tool result (RECENT → keep)
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t2",
             "content": "Budget tháng 3: Ăn uống 3,000,000 còn dư 1,000,000"},
        ]},
        # Iteration 3 - assistant calls another tool
        {"role": "assistant", "content": [
            {"type": "tool_use", "id": "t3", "name": "get_goals", "input": {}},
        ]},
        # Iteration 3 - tool result (RECENT → keep)
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t3",
             "content": "Mục tiêu: Tiết kiệm 50 triệu — đạt 30%"},
        ]},
    ]

    result = _compact_old_tool_results(messages, keep_recent=2)

    # First tool result (t1) should be compacted
    t1_msg = [m for m in result if m["role"] == "user"
              and isinstance(m.get("content"), list)
              and any(b.get("tool_use_id") == "t1" for b in m["content"]
                      if isinstance(b, dict))]
    assert len(t1_msg) == 1
    t1_content = t1_msg[0]["content"][0]["content"]
    assert "[Kết quả đã xử lý:" in t1_content

    # Recent tool results (t2, t3) should be intact
    t2_msg = [m for m in result if m["role"] == "user"
              and isinstance(m.get("content"), list)
              and any(b.get("tool_use_id") == "t2" for b in m["content"]
                      if isinstance(b, dict))]
    assert "Budget tháng 3" in t2_msg[0]["content"][0]["content"]


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
    from app.services.memory import _run_review, _session_turn_counts, maybe_trigger_review

    session_id = uuid.uuid4()
    _session_turn_counts.pop(str(session_id), None)

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

    # Cleanup
    _session_turn_counts.pop(str(session_id), None)


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


async def test_review_cadence_fires_then_facts_in_next_prompt(db: AsyncSession):
    """End-to-end: turn accumulation → review fires → facts appear in prompt.

    Simulates:
    1. User chats for N turns (cadence threshold)
    2. Background review fires and extracts facts
    3. Next session's system prompt includes those facts
    """
    from app.services.memory import (
        _run_review,
        _session_turn_counts,
        build_facts_prompt,
        maybe_trigger_review,
    )

    session_id = uuid.uuid4()
    _session_turn_counts.pop(str(session_id), None)

    messages = [
        {"role": "user", "content": "Tôi chi 3 triệu cho ăn uống mỗi tháng"},
        {"role": "assistant", "content": "Ghi nhận chi tiêu ăn uống."},
    ]

    # Step 1: Accumulate turns until cadence fires
    review_task = None

    with patch("app.services.memory.settings") as mock_settings, \
         patch("app.services.memory.asyncio") as mock_asyncio:
        mock_settings.agent_review_cadence = 3

        # Capture the coroutine when create_task is called
        def capture_task(coro):
            nonlocal review_task
            review_task = coro
            return MagicMock()

        mock_asyncio.create_task = capture_task

        # Turn 1, 2: no fire
        await maybe_trigger_review(session_id, messages)
        await maybe_trigger_review(session_id, messages)
        assert review_task is None

        # Turn 3: fire!
        await maybe_trigger_review(session_id, messages)
        assert review_task is not None

    # Step 2: Execute the review (would normally run as background task)
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps([
        {"fact": "Chi 3 triệu/tháng cho ăn uống", "category": "habit"},
    ]))]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with _patch_get_session(db), \
         patch("app.services.memory.anthropic.AsyncAnthropic", return_value=mock_client), \
         patch("app.services.memory.settings") as s:
        s.anthropic_api_key = "key"
        s.agent_review_model = "claude-haiku-4-5-20251001"
        # Execute the captured coroutine
        await review_task

    # Step 3: Verify fact is in DB and appears in next prompt
    rows = (await db.execute(select(UserFact))).scalars().all()
    assert len(rows) == 1
    assert rows[0].fact == "Chi 3 triệu/tháng cho ăn uống"

    with _patch_get_session(db):
        prompt = await build_facts_prompt()

    assert "Chi 3 triệu/tháng cho ăn uống" in prompt
    assert "(Thói quen)" in prompt

    _session_turn_counts.pop(str(session_id), None)


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
