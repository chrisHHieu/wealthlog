"""Unit tests for short-term memory compaction — all pure functions, no DB."""

import json

from app.services.agent import (
    _cap_oversized_turn,
    _compact_history,
    _compact_tool_results,
    _is_assistant_final,
    _prepend_truncation_note,
    _split_turns,
    _turn_size_chars,
)

# ── Helpers ─────────────────────────────────────────────────────────────────


def _user(text: str) -> dict:
    return {"role": "user", "content": text}


def _asst_text(text: str) -> dict:
    return {"role": "assistant", "content": text}


def _asst_tool(tid: str, name: str = "x", inp: dict | None = None) -> dict:
    return {"role": "assistant", "content": [
        {"type": "tool_use", "id": tid, "name": name, "input": inp or {}},
    ]}


def _tool_result(tid: str, content: str) -> dict:
    return {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tid, "content": content},
    ]}


def _make_turn(n: int, tool_chars: int = 3000) -> list[dict]:
    return [
        _user(f"q{n}"),
        _asst_tool(f"t{n}"),
        _tool_result(f"t{n}", "X" * tool_chars),
        _asst_text(f"a{n}"),
    ]


# ── _is_assistant_final ─────────────────────────────────────────────────────


def test_is_final_string_content():
    assert _is_assistant_final(_asst_text("hi")) is True


def test_is_final_user_never_final():
    assert _is_assistant_final(_user("hi")) is False


def test_is_final_tool_use_not_final():
    assert _is_assistant_final(_asst_tool("t1")) is False


def test_is_final_empty_list_is_final():
    # Edge: empty content list → no tool_use blocks → final.
    # This reflects Claude occasionally emitting empty content on stop.
    assert _is_assistant_final({"role": "assistant", "content": []}) is True


def test_is_final_mixed_text_and_tool_not_final():
    msg = {"role": "assistant", "content": [
        {"type": "text", "text": "thinking..."},
        {"type": "tool_use", "id": "t1", "name": "x", "input": {}},
    ]}
    assert _is_assistant_final(msg) is False


def test_is_final_text_only_block_is_final():
    msg = {"role": "assistant", "content": [
        {"type": "text", "text": "answer"},
    ]}
    assert _is_assistant_final(msg) is True


# ── _split_turns ────────────────────────────────────────────────────────────


def test_split_turns_simple_two_turns():
    msgs = [_user("q1"), _asst_text("a1"), _user("q2"), _asst_text("a2")]
    turns = _split_turns(msgs)
    assert len(turns) == 2
    assert len(turns[0]) == 2
    assert len(turns[1]) == 2


def test_split_turns_with_tool_chain():
    msgs = [
        _user("q1"),
        _asst_tool("t1"),
        _tool_result("t1", "result"),
        _asst_text("a1"),
    ]
    turns = _split_turns(msgs)
    assert len(turns) == 1
    assert len(turns[0]) == 4


def test_split_turns_incomplete_tail_captured():
    # A trailing user-only turn (mid-request) must still be returned, not dropped.
    msgs = [_user("q1")]
    turns = _split_turns(msgs)
    assert len(turns) == 1


def test_split_turns_empty_assistant_ends_turn():
    # Edge: Claude sometimes returns empty content blocks → counted as final.
    msgs = [
        _user("q1"),
        {"role": "assistant", "content": []},
        _user("q2"),
        _asst_text("a2"),
    ]
    turns = _split_turns(msgs)
    assert len(turns) == 2


# ── _compact_tool_results ───────────────────────────────────────────────────


def test_compact_results_truncates_oversized():
    msgs = [_tool_result("t1", "X" * 5000)]
    out = _compact_tool_results(msgs, max_chars=300)
    content = out[0]["content"][0]["content"]
    assert len(content) < 400
    assert "truncated" in content


def test_compact_results_preserves_small():
    msgs = [_tool_result("t1", "small")]
    out = _compact_tool_results(msgs, max_chars=300)
    assert out[0]["content"][0]["content"] == "small"


def test_compact_results_preserves_tool_use_id():
    msgs = [_tool_result("unique-id", "X" * 5000)]
    out = _compact_tool_results(msgs, max_chars=300)
    assert out[0]["content"][0]["tool_use_id"] == "unique-id"


def test_compact_results_passes_through_string_content():
    msgs = [_user("hi")]
    out = _compact_tool_results(msgs, max_chars=100)
    assert out == msgs


def test_compact_results_preserves_tool_use_blocks():
    msgs = [_asst_tool("t1", "search", {"q": "big"})]
    out = _compact_tool_results(msgs, max_chars=100)
    assert out == msgs


# ── _prepend_truncation_note ────────────────────────────────────────────────


def test_prepend_note_injects_into_string():
    msgs = [_user("original"), _asst_text("a")]
    out = _prepend_truncation_note(msgs, dropped=5)
    assert out[0]["role"] == "user"
    assert "5" in out[0]["content"]
    assert "original" in out[0]["content"]


def test_prepend_note_injects_into_list_content():
    msgs = [{"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": "r"},
    ]}]
    out = _prepend_truncation_note(msgs, dropped=3)
    blocks = out[0]["content"]
    assert blocks[0]["type"] == "text"
    assert "3" in blocks[0]["text"]
    assert blocks[1]["type"] == "tool_result"


def test_prepend_note_skips_assistant_until_user():
    msgs = [_asst_text("weird start"), _user("q1"), _asst_text("a1")]
    out = _prepend_truncation_note(msgs, dropped=2)
    assert out[0] == _asst_text("weird start")  # untouched
    assert "2" in out[1]["content"]


def test_prepend_note_is_bilingual():
    # Contract: English + Vietnamese markers so either-language users see context.
    msgs = [_user("hi")]
    out = _prepend_truncation_note(msgs, dropped=1)
    text = out[0]["content"]
    assert "System" in text      # English marker
    assert "lượt" in text        # Vietnamese marker


def test_prepend_note_no_user_returns_original():
    msgs = [_asst_text("a1"), _asst_text("a2")]
    out = _prepend_truncation_note(msgs, dropped=2)
    assert out == msgs


# ── _turn_size_chars ────────────────────────────────────────────────────────


def test_turn_size_string_content():
    assert _turn_size_chars([_user("hello")]) == 5


def test_turn_size_text_and_tool_use_blocks():
    turn = [{"role": "assistant", "content": [
        {"type": "text", "text": "hi"},
        {"type": "tool_use", "id": "t1", "name": "x", "input": {"q": "v"}},
    ]}]
    expected = 2 + len(json.dumps({"q": "v"}))
    assert _turn_size_chars(turn) == expected


def test_turn_size_tool_result_string():
    turn = [_tool_result("t1", "result-text")]
    assert _turn_size_chars(turn) == len("result-text")


def test_turn_size_thinking_block():
    turn = [{"role": "assistant", "content": [
        {"type": "thinking", "thinking": "reasoning text", "signature": "sig"},
    ]}]
    assert _turn_size_chars(turn) == len("reasoning text")


# ── _cap_oversized_turn ─────────────────────────────────────────────────────


def test_cap_turn_under_limit_passthrough():
    turn = [_user("q"), _asst_text("a")]
    out = _cap_oversized_turn(turn, max_chars=1000, fallback_chars=300)
    assert out == turn


def test_cap_turn_multi_result_preserves_last():
    turn = [
        _user("q"),
        _asst_tool("t1"),
        _tool_result("t1", "A" * 5000),
        _asst_tool("t2"),
        _tool_result("t2", "B" * 5000),
        _asst_text("final"),
    ]
    out = _cap_oversized_turn(turn, max_chars=1000, fallback_chars=300)
    first_result = out[2]["content"][0]["content"]
    last_result = out[4]["content"][0]["content"]
    assert len(first_result) < 400  # truncated
    assert len(last_result) == 5000  # intact


def test_cap_turn_single_result_truncates_it():
    turn = [
        _user("q"),
        _asst_tool("t1"),
        _tool_result("t1", "A" * 5000),
        _asst_text("final"),
    ]
    out = _cap_oversized_turn(turn, max_chars=500, fallback_chars=300)
    assert len(out[2]["content"][0]["content"]) < 400


# ── _compact_history (end-to-end 3-tier) ────────────────────────────────────


def _call(msgs, *, max_turns=20, keep=3, old=300, recent_cap=99999):
    return _compact_history(
        msgs,
        max_turns=max_turns,
        keep_recent_turns=keep,
        old_tool_result_chars=old,
        recent_turn_max_chars=recent_cap,
    )


def test_compact_below_keep_recent_is_noop():
    msgs = []
    for i in range(2):
        msgs.extend(_make_turn(i))
    out, dropped = _call(msgs)
    assert dropped == 0
    assert out == msgs


def test_compact_at_keep_recent_is_noop():
    msgs = []
    for i in range(3):
        msgs.extend(_make_turn(i))
    out, dropped = _call(msgs)
    assert dropped == 0


def test_compact_middle_truncates_recent_intact():
    msgs = []
    for i in range(10):
        msgs.extend(_make_turn(i))
    out, dropped = _call(msgs)
    assert dropped == 0
    turns_out = _split_turns(out)
    assert len(turns_out) == 10
    # Middle turns: first 7 → tool_results truncated
    for turn in turns_out[:7]:
        for msg in turn:
            if not isinstance(msg["content"], list):
                continue
            for b in msg["content"]:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    assert len(b["content"]) < 400
    # Recent turns: last 3 → full size
    for turn in turns_out[-3:]:
        for msg in turn:
            if not isinstance(msg["content"], list):
                continue
            for b in msg["content"]:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    assert len(b["content"]) == 3000


def test_compact_over_max_turns_drops():
    msgs = []
    for i in range(25):
        msgs.extend(_make_turn(i))
    out, dropped = _call(msgs)
    assert dropped == 5
    assert len(_split_turns(out)) == 20


def test_compact_first_message_is_user_after_drop():
    """Claude API strictly requires the first message to be role=user."""
    msgs = []
    for i in range(25):
        msgs.extend(_make_turn(i))
    out, _ = _call(msgs)
    assert out[0]["role"] == "user"


def test_compact_truncation_note_mentions_count():
    msgs = []
    for i in range(25):
        msgs.extend(_make_turn(i))
    out, dropped = _call(msgs)
    first_content = out[0]["content"]
    text = first_content if isinstance(first_content, str) else first_content[0]["text"]
    assert str(dropped) in text


def test_compact_role_alternation_preserved():
    """Critical invariant: after compaction, user/assistant must strictly alternate."""
    msgs = []
    for i in range(30):
        msgs.extend(_make_turn(i))
    out, _ = _call(msgs)
    roles = [m["role"] for m in out]
    for i in range(1, len(roles)):
        assert roles[i] != roles[i - 1], (
            f"Role alternation broken at index {i}: {roles[i - 1]} → {roles[i]}"
        )


def test_compact_tool_use_result_pairs_intact():
    """Every tool_use must have a matching tool_result somewhere after it."""
    msgs = []
    for i in range(30):
        msgs.extend(_make_turn(i))
    out, _ = _call(msgs)

    uses, results = set(), set()
    for msg in out:
        if not isinstance(msg.get("content"), list):
            continue
        for b in msg["content"]:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use":
                uses.add(b["id"])
            elif b.get("type") == "tool_result":
                results.add(b["tool_use_id"])
    assert uses == results


def test_compact_per_turn_cap_kicks_in():
    """A recent turn exceeding recent_turn_max_chars must get middle-tier treatment."""
    # Single turn with 3 tool calls each 5000 chars → well over a 4000 cap
    heavy_turn = [
        _user("big"),
        _asst_tool("t1"), _tool_result("t1", "A" * 5000),
        _asst_tool("t2"), _tool_result("t2", "B" * 5000),
        _asst_tool("t3"), _tool_result("t3", "C" * 5000),
        _asst_text("final"),
    ]
    # Put it in recent tier by making it the only turn beyond keep_recent
    msgs = [*_make_turn(0), *_make_turn(1), *heavy_turn]
    out, dropped = _call(msgs, max_turns=20, keep=3, old=300, recent_cap=4000)
    assert dropped == 0
    # The last-in-turn tool_result (t3) stays full; earlier ones (t1, t2) shrink
    turns_out = _split_turns(out)
    recent_turns = turns_out[-3:]
    heavy = recent_turns[-1]
    sizes = []
    for msg in heavy:
        if not isinstance(msg["content"], list):
            continue
        for b in msg["content"]:
            if isinstance(b, dict) and b.get("type") == "tool_result":
                sizes.append(len(b["content"]))
    assert sizes[0] < 400 and sizes[1] < 400  # truncated
    assert sizes[2] == 5000                    # last preserved
