"""AI Agent service — connects Claude API to MCP tools."""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone

import anthropic

from app.config import settings
from app.logging_config import get_logger
from app.mcp.server import mcp
from app.mcp.tools_discovery import build_schema_summary
from app.services.memory import build_facts_prompt
from app.services.summary import build_summaries_prompt, summarize_session
from app.services.token_budget import estimate_request_tokens

logger = get_logger(__name__)

_SYSTEM_BASE = (
    "You are WealthLog AI — an intelligent personal finance assistant. "
    "You help users manage income, expenses, budgets, savings goals, and investments.\n\n"
    "Language:\n"
    "- Respond in the SAME language the user writes in. Default to Vietnamese "
    "when the user's language is ambiguous (one-word messages, emoji-only, etc.).\n\n"
    "General rules:\n"
    "- Always use tools to fetch real data. NEVER fabricate numbers.\n"
    "- Default currency: VND. Number format: use commas (e.g., 1,000,000).\n"
    "- Month format: YYYY-MM. Date format: YYYY-MM-DD.\n"
    "- Keep answers concise, clear, with insight.\n"
    "- For overview questions, call multiple tools to build a complete picture.\n"
    "- Give specific advice when appropriate.\n"
    "- When creating transactions, use the exact category_name from the list below.\n\n"
    "Tool selection priority:\n"
    "1. PREFER specialized tools (get_spending_by_category, get_budget_status, "
    "get_financial_summary, get_goals, get_portfolio, search_transactions…) "
    "— fast, safe, pre-formatted.\n"
    "2. Use query_database ONLY when the question goes BEYOND specialized-tool scope "
    "(e.g., group by weekday, anomaly detection, custom analytics).\n"
    "3. Database schema is in the <database_schema> block below — READ it before "
    "writing SQL. No need to call get_database_schema again.\n\n"
    "Writing SQL:\n"
    "- Check enum values ([enum: A | B | C]) and foreign keys (→ table.col) in schema.\n"
    "- Money columns are double precision → cast ::numeric before ROUND when needed.\n"
    "- Return raw numbers; format in the reply text.\n"
    "- On error, read the 'Hint' field — it points to the root cause.\n\n"
    "Context truncation:\n"
    "- If you see a message starting with '[System: N older turns were truncated' / "
    "'[System: N lượt cũ đã bị lược bỏ', DO NOT try to reconstruct the dropped "
    "content. Use user facts and session summaries from the system prompt to "
    "answer questions about earlier conversation history."
)

# MCP resource URIs to inject into system prompt.
# The guide resource was dropped — tool docstrings + _SYSTEM_BASE already cover that ground.
_RESOURCE_URIS = [
    "wealthlog://profile",
    "wealthlog://categories",
]


def _now_vn() -> str:
    """Current datetime in Vietnam timezone (UTC+7)."""
    vn_tz = timezone(timedelta(hours=7))
    now = datetime.now(vn_tz)
    weekdays = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
    return f"{weekdays[now.weekday()]}, {now.strftime('%d/%m/%Y %H:%M')} (GMT+7)"


async def _build_system_blocks() -> list[dict]:
    """Build the system prompt as two blocks: stable (cached) + dynamic (uncached).

    The stable block — base instructions, DB schema, MCP resources — is marked
    ``cache_control: ephemeral`` so Anthropic reuses it for 5 minutes. Anything
    that changes per-request (timestamp, summaries, facts) lives in a trailing
    uncached block; otherwise a single fact update or ticking minute would bust
    the cache on the multi-KB schema every turn.
    """
    stable_parts = [_SYSTEM_BASE]

    try:
        schema = await build_schema_summary()
        stable_parts.append(f"\n---\n<database_schema>\n{schema}\n</database_schema>")
    except Exception:
        logger.warning("Failed to preload database schema")

    for uri in _RESOURCE_URIS:
        try:
            contents = await mcp.read_resource(uri)
            for item in contents:
                if hasattr(item, "content") and item.content:
                    stable_parts.append(f"\n---\n## {uri}\n{item.content}")
        except Exception:
            logger.warning("Failed to load resource: %s", uri)

    dynamic_parts = [f"Thời gian hiện tại: {_now_vn()}"]

    summaries_block = await build_summaries_prompt()
    if summaries_block:
        dynamic_parts.append(f"\n---\n{summaries_block}")

    facts_block = await build_facts_prompt()
    if facts_block:
        dynamic_parts.append(f"\n---\n{facts_block}")

    return [
        {
            "type": "text",
            "text": "\n".join(stable_parts),
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": "\n".join(dynamic_parts),
        },
    ]

# Max tool-call iterations to prevent infinite loops
MAX_ITERATIONS = 15


async def _get_tools_for_claude() -> list[dict]:
    """Convert MCP tools to Anthropic tool format."""
    mcp_tools = await mcp.list_tools()
    tools = []
    for t in mcp_tools:
        tool_def = {
            "name": t.name,
            "description": t.description or "",
            "input_schema": t.inputSchema,
        }
        tools.append(tool_def)
    return tools


async def _execute_tool(name: str, arguments: dict) -> str:
    """Execute an MCP tool and return the text result."""
    try:
        result = await mcp.call_tool(name, arguments)
        # call_tool returns (list[TextContent], dict) or similar
        if isinstance(result, tuple):
            contents = result[0]
        else:
            contents = result

        texts = []
        if isinstance(contents, list):
            for item in contents:
                if hasattr(item, "text"):
                    texts.append(item.text)
                elif isinstance(item, str):
                    texts.append(item)
        elif isinstance(contents, str):
            texts.append(contents)

        return "\n".join(texts) if texts else "No results."
    except Exception as e:
        logger.exception("Tool execution error: %s", name)
        return f"Error calling tool {name}: {e}"


def _truncate_tool_result(text: str, max_chars: int) -> str:
    """Truncate a tool result that exceeds max_chars, preserving useful context."""
    if len(text) <= max_chars:
        return text

    cut = max_chars - 80
    truncated = text[:cut]

    last_newline = truncated.rfind("\n")
    if last_newline > cut * 0.7:
        truncated = truncated[:last_newline]

    remaining = len(text) - len(truncated)
    return (
        f"{truncated}\n\n"
        f"[... {remaining:,} chars truncated. Re-call with a smaller limit for details.]"
    )


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
    max_turns: int,
    keep_recent_turns: int,
    old_tool_result_chars: int,
    recent_turn_max_chars: int,
) -> tuple[list[dict], int]:
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
        return out, 0

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
    return compacted, dropped


# SSE event types
EVENT_THINKING_START = "thinking_start"
EVENT_THINKING_DELTA = "thinking_delta"
EVENT_THINKING_STOP = "thinking_stop"
EVENT_TEXT_START = "text_start"
EVENT_TEXT_DELTA = "text_delta"
EVENT_TEXT_STOP = "text_stop"
EVENT_TOOL_START = "tool_start"
EVENT_TOOL_INPUT = "tool_input"
EVENT_TOOL_DONE = "tool_done"
EVENT_ITERATION = "iteration"
EVENT_DONE = "done"
EVENT_ERROR = "error"
# Internal events — consumed by the chat router for persistence, not sent to the client.
# Carry the full Anthropic content blocks so we can rebuild the exact conversation later.
EVENT_PERSIST_ASSISTANT = "_persist_assistant"
EVENT_PERSIST_TOOL_RESULTS = "_persist_tool_results"


def _sse_event(event: str, data: dict) -> str:
    """Format an SSE event string."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _build_thinking_param() -> dict | None:
    """Build the `thinking` parameter for Claude API if enabled."""
    if not settings.agent_thinking_enabled:
        return None
    return {
        "type": "enabled",
        "budget_tokens": settings.agent_thinking_budget,
    }


async def run_agent_stream(
    messages: list[dict],
    session_id: uuid.UUID | None = None,
) -> AsyncGenerator[str, None]:
    """Run the agent loop, yielding SSE events in ReAct order.

    Events (in arrival order per iteration):
    - iteration:      {"n": 1}
    - thinking_start: {"step_id": "..."}
    - thinking_delta: {"step_id": "...", "text": "..."}
    - thinking_stop:  {"step_id": "..."}
    - text_start:     {"step_id": "..."}
    - text_delta:     {"step_id": "...", "text": "..."}
    - text_stop:      {"step_id": "...", "final": bool}
    - tool_start:     {"step_id": "...", "id": "...", "name": "..."}
    - tool_input:     {"step_id": "...", "id": "...", "input": {...}}
    - tool_done:      {"step_id": "...", "id": "...", "result": "..."}
    - done:           {}
    - error:          {"message": "..."}
    """
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    tools = await _get_tools_for_claude()
    system_blocks = await _build_system_blocks()

    max_result_chars = settings.agent_tool_result_max_chars
    thinking_param = _build_thinking_param()

    claude_messages, dropped = _compact_history(
        [{"role": m["role"], "content": m["content"]} for m in messages],
        max_turns=settings.agent_max_turns_in_context,
        keep_recent_turns=settings.agent_keep_recent_turns,
        old_tool_result_chars=settings.agent_old_turn_tool_result_chars,
        recent_turn_max_chars=settings.agent_recent_turn_max_chars,
    )

    # Turns just fell off the live window. Refresh the episodic summary now so
    # the content isn't lost until the 30-min idle sweep catches up — otherwise
    # long back-to-back sessions leak context between the drop and next idle.
    if dropped > 0 and session_id is not None:
        asyncio.create_task(summarize_session(session_id))

    # One pre-send token count per request. We skip recounting on follow-up
    # iterations because later iterations only append tool_results to the same
    # request shape — within a bounded factor of the first count — and the
    # endpoint round-trip isn't free of latency.
    est_tokens = await estimate_request_tokens(
        client, settings.agent_model, system_blocks, claude_messages, tools,
    )
    if est_tokens is not None:
        logger.info("Pre-send input tokens: %d", est_tokens)
        if est_tokens > settings.agent_max_input_tokens:
            logger.warning(
                "Input tokens %d exceed soft budget %d — context may be unhealthy",
                est_tokens, settings.agent_max_input_tokens,
            )

    for iteration in range(MAX_ITERATIONS):
        logger.info("Agent iteration %d", iteration + 1)
        yield _sse_event(EVENT_ITERATION, {"n": iteration + 1})

        # Track all content blocks in order — needed for proper assistant history
        # and for preserving thinking signatures required by the API.
        blocks: list[dict] = []  # each: {index, type, ...block-specific}
        stop_reason = None
        usage = {"input": 0, "cache_read": 0, "cache_write": 0, "output": 0}

        stream_kwargs: dict = {
            "model": settings.agent_model,
            "max_tokens": settings.agent_max_tokens,
            "system": system_blocks,
            "messages": claude_messages,
            "tools": tools,
        }
        if thinking_param:
            stream_kwargs["thinking"] = thinking_param

        async with client.messages.stream(**stream_kwargs) as stream:
            async for event in stream:
                if event.type == "message_start":
                    u = event.message.usage
                    usage["input"] = u.input_tokens
                    usage["cache_read"] = getattr(u, "cache_read_input_tokens", 0) or 0
                    usage["cache_write"] = getattr(u, "cache_creation_input_tokens", 0) or 0
                    usage["output"] = u.output_tokens
                elif event.type == "content_block_start":
                    idx = event.index
                    block = event.content_block
                    step_id = f"{iteration}-{idx}"

                    if block.type == "thinking":
                        blocks.append({
                            "index": idx,
                            "type": "thinking",
                            "step_id": step_id,
                            "thinking": "",
                            "signature": "",
                        })
                        yield _sse_event(EVENT_THINKING_START, {"step_id": step_id})

                    elif block.type == "text":
                        blocks.append({
                            "index": idx,
                            "type": "text",
                            "step_id": step_id,
                            "text": "",
                        })
                        yield _sse_event(EVENT_TEXT_START, {"step_id": step_id})

                    elif block.type == "tool_use":
                        blocks.append({
                            "index": idx,
                            "type": "tool_use",
                            "step_id": step_id,
                            "id": block.id,
                            "name": block.name,
                            "input_json": "",
                        })
                        yield _sse_event(EVENT_TOOL_START, {
                            "step_id": step_id,
                            "id": block.id,
                            "name": block.name,
                        })

                elif event.type == "content_block_delta":
                    idx = event.index
                    # Find block by index (blocks list is append-only, ordered)
                    block = next((b for b in blocks if b["index"] == idx), None)
                    if block is None:
                        continue

                    if event.delta.type == "text_delta":
                        block["text"] += event.delta.text
                        yield _sse_event(EVENT_TEXT_DELTA, {
                            "step_id": block["step_id"],
                            "text": event.delta.text,
                        })
                    elif event.delta.type == "thinking_delta":
                        block["thinking"] += event.delta.thinking
                        yield _sse_event(EVENT_THINKING_DELTA, {
                            "step_id": block["step_id"],
                            "text": event.delta.thinking,
                        })
                    elif event.delta.type == "signature_delta":
                        # Signature must be preserved for extended thinking verification
                        block["signature"] += event.delta.signature
                    elif event.delta.type == "input_json_delta":
                        block["input_json"] += event.delta.partial_json

                elif event.type == "content_block_stop":
                    idx = event.index
                    block = next((b for b in blocks if b["index"] == idx), None)
                    if block is None:
                        continue

                    if block["type"] == "thinking":
                        yield _sse_event(EVENT_THINKING_STOP, {"step_id": block["step_id"]})
                    elif block["type"] == "text":
                        # "final" flag will be set correctly based on stop_reason below,
                        # but emit provisional stop for UI to finalize the text block
                        yield _sse_event(EVENT_TEXT_STOP, {
                            "step_id": block["step_id"],
                            "final": False,  # updated on done if no more tools
                        })
                    elif block["type"] == "tool_use":
                        try:
                            inp = json.loads(block["input_json"]) if block["input_json"] else {}
                        except json.JSONDecodeError:
                            inp = {}
                        yield _sse_event(EVENT_TOOL_INPUT, {
                            "step_id": block["step_id"],
                            "id": block["id"],
                            "input": inp,
                        })

                elif event.type == "message_delta":
                    stop_reason = event.delta.stop_reason
                    if hasattr(event, "usage") and event.usage is not None:
                        usage["output"] = event.usage.output_tokens

        cache_total = usage["cache_read"] + usage["cache_write"]
        cache_hit_pct = (
            round(usage["cache_read"] / cache_total * 100) if cache_total else 0
        )
        logger.info(
            "iter=%d tokens: in=%d (cache read=%d write=%d, hit=%d%%) out=%d",
            iteration + 1,
            usage["input"], usage["cache_read"], usage["cache_write"],
            cache_hit_pct, usage["output"],
        )

        # Extract tool uses and text blocks from the iteration
        tool_uses = [b for b in blocks if b["type"] == "tool_use"]

        # Build assistant message preserving block order + thinking signatures
        assistant_content = []
        for b in blocks:
            if b["type"] == "thinking":
                # Thinking blocks MUST be preserved with signature when tools used
                assistant_content.append({
                    "type": "thinking",
                    "thinking": b["thinking"],
                    "signature": b["signature"],
                })
            elif b["type"] == "text" and b["text"]:
                assistant_content.append({"type": "text", "text": b["text"]})
            elif b["type"] == "tool_use":
                try:
                    inp = json.loads(b["input_json"]) if b["input_json"] else {}
                except json.JSONDecodeError:
                    inp = {}
                assistant_content.append({
                    "type": "tool_use",
                    "id": b["id"],
                    "name": b["name"],
                    "input": inp,
                })

        # Emit full assistant blocks for persistence (router filters these out before SSE)
        yield _sse_event(EVENT_PERSIST_ASSISTANT, {"blocks": assistant_content})

        # If no tool calls, this is the final answer — we're done
        if stop_reason != "tool_use" or not tool_uses:
            break

        claude_messages.append({"role": "assistant", "content": assistant_content})

        # Execute all tool calls and feed results back
        tool_results = []
        for tu in tool_uses:
            try:
                inp = json.loads(tu["input_json"]) if tu["input_json"] else {}
            except json.JSONDecodeError:
                inp = {}

            result_text = await _execute_tool(tu["name"], inp)
            result_text = _truncate_tool_result(result_text, max_result_chars)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu["id"],
                "content": result_text,
            })

            yield _sse_event(EVENT_TOOL_DONE, {
                "step_id": tu["step_id"],
                "id": tu["id"],
                "result": result_text[:500],  # truncate for SSE
            })

        claude_messages.append({"role": "user", "content": tool_results})
        yield _sse_event(EVENT_PERSIST_TOOL_RESULTS, {"blocks": tool_results})

    yield _sse_event(EVENT_DONE, {})
