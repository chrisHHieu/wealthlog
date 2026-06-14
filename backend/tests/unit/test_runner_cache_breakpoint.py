"""Unit tests for the per-iteration message cache breakpoint."""

from app.ai.agent.runner import _with_cache_breakpoint


def test_empty_messages_pass_through():
    assert _with_cache_breakpoint([]) == []


def test_string_content_becomes_marked_text_block():
    msgs = [{"role": "user", "content": "hi"}]
    out = _with_cache_breakpoint(msgs)
    assert out[-1]["content"] == [
        {"type": "text", "text": "hi", "cache_control": {"type": "ephemeral"}}
    ]


def test_block_content_marks_only_last_block():
    msgs = [
        {"role": "user", "content": "q"},
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "t1", "content": "a"},
                {"type": "tool_result", "tool_use_id": "t2", "content": "b"},
            ],
        },
    ]
    out = _with_cache_breakpoint(msgs)
    blocks = out[-1]["content"]
    assert "cache_control" not in blocks[0]
    assert blocks[1]["cache_control"] == {"type": "ephemeral"}


def test_originals_stay_unmarked():
    """claude_messages and persisted tool_result blocks must never carry cache_control."""
    inner = {"type": "tool_result", "tool_use_id": "t1", "content": "a"}
    msgs = [
        {"role": "user", "content": "hi"},
        {"role": "user", "content": [inner]},
    ]
    _with_cache_breakpoint(msgs)
    assert msgs[0]["content"] == "hi"
    assert "cache_control" not in inner
