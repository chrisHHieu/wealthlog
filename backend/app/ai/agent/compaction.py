"""Short-term memory — turn-aware history compaction.

Three-tier strategy:
- oldest turns past ``max_turns`` are dropped entirely
- middle turns keep structure but tool_result payloads shrink
- recent turns pass through, except when a single turn exceeds the per-turn cap

Pure functions, no I/O — the agent runner wires them up with settings.
"""

import json

from app.logging_config import get_logger

logger = get_logger(__name__)


def _is_assistant_final(msg: dict) -> bool:
    """An assistant message with no tool_use block — marks the end of a turn."""
    if msg.get("role") != "assistant":
        return False
    content = msg.get("content")
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        return not any(
            isinstance(b, dict) and b.get("type") == "tool_use"
            for b in content
        )
    return False


def _split_turns(messages: list[dict]) -> list[list[dict]]:
    """Group messages into turns ending at assistant-final boundaries.

    A turn spans one user request plus its full tool chain and final answer,
    so tool_use/tool_result pairs are never split across the boundary — which
    Claude's API strictly requires.
    """
    turns: list[list[dict]] = []
    current: list[dict] = []
    for msg in messages:
        current.append(msg)
        if _is_assistant_final(msg):
            turns.append(current)
            current = []
    if current:
        turns.append(current)
    return turns


# Reserve for the truncation note appended below — keeps total output within
# max_chars. Update if the note text grows.
_TRUNCATION_NOTE_RESERVE = 130


def _truncate_tool_result(text: str, max_chars: int) -> str:
    """Truncate a tool result that exceeds max_chars, preserving useful context."""
    if len(text) <= max_chars:
        return text

    cut = max(0, max_chars - _TRUNCATION_NOTE_RESERVE)
    truncated = text[:cut]

    last_newline = truncated.rfind("\n")
    if last_newline > cut * 0.7:
        truncated = truncated[:last_newline]

    remaining = len(text) - len(truncated)
    return (
        f"{truncated}\n\n"
        f"[... {remaining:,} chars truncated — page with offset or narrow the "
        f"query; a smaller limit alone returns the same head again.]"
    )


def _compact_tool_results(messages: list[dict], max_chars: int) -> list[dict]:
    """Truncate tool_result.content in each message, keeping tool_use_id intact."""
    out: list[dict] = []
    for msg in messages:
        content = msg.get("content")
        if not isinstance(content, list):
            out.append(msg)
            continue
        new_blocks = []
        for block in content:
            is_result = (
                isinstance(block, dict)
                and block.get("type") == "tool_result"
                and isinstance(block.get("content"), str)
            )
            if is_result and len(block["content"]) > max_chars:
                new_blocks.append({
                    "type": "tool_result",
                    "tool_use_id": block["tool_use_id"],
                    "content": _truncate_tool_result(block["content"], max_chars),
                })
            else:
                new_blocks.append(block)
        out.append({"role": msg["role"], "content": new_blocks})
    return out


def _prepend_truncation_note(messages: list[dict], dropped: int) -> list[dict]:
    """Inject a bilingual system note into the first user message.

    Anthropic requires the first message to be ``user`` and forbids orphan
    system turns mid-conversation, so we piggyback on the user content instead
    of inserting a new message. Handles both string and block-list content.
    The note is bilingual (EN + VN) so the agent's language-matching rule
    works regardless of which language the user is currently writing in.
    """
    note = (
        f"[System: {dropped} older turns were truncated due to context limits. "
        f"Refer to user facts and session summaries in the system prompt for "
        f"earlier context. — {dropped} lượt cũ đã bị lược bỏ do giới hạn ngữ "
        f"cảnh; xem user facts và session summaries trong system prompt.]\n\n"
    )
    out = list(messages)
    for i, msg in enumerate(out):
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if isinstance(content, str):
            out[i] = {"role": "user", "content": note + content}
        elif isinstance(content, list):
            out[i] = {
                "role": "user",
                "content": [{"type": "text", "text": note}, *content],
            }
        break
    return out


def _turn_size_chars(turn: list[dict]) -> int:
    """Approximate char count of a turn — covers all block types we emit.

    Not token-accurate (use ``token_budget.estimate_request_tokens`` for that),
    but cheap and monotonic, which is all we need to decide whether a turn
    crossed the per-turn cap.
    """
    total = 0
    for msg in turn:
        content = msg.get("content")
        if isinstance(content, str):
            total += len(content)
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text":
                    total += len(block.get("text", ""))
                elif btype == "thinking":
                    total += len(block.get("thinking", ""))
                elif btype == "tool_use":
                    total += len(json.dumps(block.get("input") or {}))
                elif btype == "tool_result":
                    c = block.get("content")
                    if isinstance(c, str):
                        total += len(c)
                    elif isinstance(c, list):
                        for b in c:
                            if isinstance(b, dict):
                                total += len(b.get("text", ""))
    return total


def _cap_oversized_turn(
    turn: list[dict],
    max_chars: int,
    fallback_chars: int,
) -> list[dict]:
    """If a recent turn is too bloated, compact all but its last tool_result.

    A single bad turn (e.g. the agent chained 15 tool calls) can blow the
    context budget on its own. We keep the last tool_result at full size
    because the final assistant answer was most likely grounded in it, and
    shrink earlier tool_results to the middle-tier limit. If there's only one
    tool_result in the turn, we shrink that — there's nothing else to choose.
    """
    if _turn_size_chars(turn) <= max_chars:
        return turn

    result_indices = [
        i for i, msg in enumerate(turn)
        if isinstance(msg.get("content"), list) and any(
            isinstance(b, dict) and b.get("type") == "tool_result"
            for b in msg["content"]
        )
    ]
    if len(result_indices) <= 1:
        return _compact_tool_results(turn, fallback_chars)

    keep_last = result_indices[-1]
    out: list[dict] = []
    for i, msg in enumerate(turn):
        if i == keep_last or i not in result_indices:
            out.append(msg)
        else:
            out.extend(_compact_tool_results([msg], fallback_chars))
    return out


def _compact_history(
    messages: list[dict],
    max_turns: int | None = None,
    keep_recent_turns: int = 3,
    old_tool_result_chars: int = 300,
    recent_turn_max_chars: int = 20_000,
) -> tuple[list[dict], int] | list[dict]:
    """Apply 3-tier compaction; return (compacted_messages, dropped_turn_count).

    - Oldest turns beyond ``max_turns`` are dropped entirely; a bilingual
      system note is injected into the first remaining user message. Long-term
      facts + session summaries carry the semantic load.
    - Middle turns (between the drop boundary and the recent window) keep
      their structure but have tool_result payloads truncated.
    - Recent turns pass through verbatim, except for ones whose own size
      exceeds ``recent_turn_max_chars`` — those fall back to middle-tier
      truncation on all but their last tool_result.

    The dropped count is returned so callers can trigger a mid-session summary
    before the content is gone from the conversation forever.
    """
    legacy_list_return = max_turns is None
    max_turns = max_turns or 20
    turns = _split_turns(messages)
    n = len(turns)

    # Short session: no middle tier, no drops — just guard against one-turn
    # bloat so an early chain of 15 tool calls can't blow budget by itself.
    if n <= keep_recent_turns:
        out: list[dict] = []
        for turn in turns:
            out.extend(_cap_oversized_turn(
                turn, recent_turn_max_chars, old_tool_result_chars,
            ))
        return out if legacy_list_return else (out, 0)

    recent_start = n - keep_recent_turns
    middle_start = max(0, n - max_turns)
    dropped = middle_start

    middle = turns[middle_start:recent_start]
    recent = turns[recent_start:]

    compacted: list[dict] = []
    for turn in middle:
        compacted.extend(_compact_tool_results(turn, old_tool_result_chars))
    for turn in recent:
        compacted.extend(_cap_oversized_turn(
            turn, recent_turn_max_chars, old_tool_result_chars,
        ))

    if dropped > 0:
        compacted = _prepend_truncation_note(compacted, dropped)

    logger.info(
        "History compacted: %d turns → dropped=%d middle=%d recent=%d",
        n, dropped, len(middle), len(recent),
    )
    return compacted if legacy_list_return else (compacted, dropped)
