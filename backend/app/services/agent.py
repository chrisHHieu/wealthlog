"""AI Agent service — connects Claude API to MCP tools."""

import json
from collections.abc import AsyncGenerator
from datetime import datetime, timezone, timedelta

import anthropic

from app.config import settings
from app.logging_config import get_logger
from app.mcp.server import mcp
from app.mcp.tools_discovery import build_schema_summary
from app.services.memory import build_facts_prompt

logger = get_logger(__name__)

_SYSTEM_BASE = (
    "Bạn là WealthLog AI — trợ lý tài chính cá nhân thông minh. "
    "Bạn giúp người dùng quản lý thu chi, ngân sách, mục tiêu tiết kiệm và đầu tư.\n\n"
    "Quy tắc chung:\n"
    "- Luôn dùng tool để lấy dữ liệu thực, KHÔNG bịa số liệu.\n"
    "- Tiền tệ mặc định: VND. Format số: dùng dấu phẩy (ví dụ: 1,000,000).\n"
    "- Format tháng: YYYY-MM. Format ngày: YYYY-MM-DD.\n"
    "- Trả lời ngắn gọn, rõ ràng, có insight.\n"
    "- Khi user hỏi tổng quan, gọi nhiều tool để có bức tranh đầy đủ.\n"
    "- Đưa ra lời khuyên cụ thể khi phù hợp.\n"
    "- Khi tạo giao dịch, dùng đúng category_name từ danh sách bên dưới.\n\n"
    "Thứ tự ưu tiên khi chọn tool:\n"
    "1. ƯU TIÊN tool chuyên dụng (get_spending_by_category, get_budget_status, "
    "get_financial_summary, get_goals, get_portfolio, search_transactions…) "
    "— nhanh, an toàn, kết quả đã format.\n"
    "2. Chỉ dùng query_database khi câu hỏi VƯỢT NGOÀI phạm vi tool chuyên dụng "
    "(vd: group by thứ trong tuần, anomaly detection, analytics đặc biệt).\n"
    "3. Schema database đã có trong block <database_schema> bên dưới — "
    "ĐỌC nó trước khi viết SQL. KHÔNG cần gọi get_database_schema nữa.\n\n"
    "Khi viết SQL:\n"
    "- Xem enum values ([enum: A | B | C]) và foreign keys (→ table.col) trong schema.\n"
    "- Cột tiền là double precision → cast ::numeric trước ROUND nếu cần.\n"
    "- Trả số thô, format ở câu trả lời.\n"
    "- Nếu lỗi, đọc 'Gợi ý' trong error message — nó chỉ ra nguyên nhân cụ thể."
)

# MCP resource URIs to inject into system prompt
_RESOURCE_URIS = [
    "wealthlog://profile",
    "wealthlog://categories",
    "wealthlog://guide",
]


def _now_vn() -> str:
    """Current datetime in Vietnam timezone (UTC+7)."""
    vn_tz = timezone(timedelta(hours=7))
    now = datetime.now(vn_tz)
    weekdays = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
    return f"{weekdays[now.weekday()]}, {now.strftime('%d/%m/%Y %H:%M')} (GMT+7)"


async def _build_system_prompt() -> str:
    """Build system prompt with live MCP resources, schema, and user facts injected."""
    sections = [f"Thời gian hiện tại: {_now_vn()}\n\n{_SYSTEM_BASE}"]

    # Preload DB schema so the agent never has to guess enum/FK/column info.
    try:
        schema = await build_schema_summary()
        sections.append(f"\n---\n<database_schema>\n{schema}\n</database_schema>")
    except Exception:
        logger.warning("Failed to preload database schema")

    for uri in _RESOURCE_URIS:
        try:
            contents = await mcp.read_resource(uri)
            for item in contents:
                if hasattr(item, "content") and item.content:
                    sections.append(f"\n---\n## {uri}\n{item.content}")
        except Exception:
            logger.warning("Failed to load resource: %s", uri)

    # Inject long-term user facts
    facts_block = await build_facts_prompt()
    if facts_block:
        sections.append(f"\n---\n{facts_block}")

    return "\n".join(sections)


def _system_with_cache(system_text: str) -> list[dict]:
    """Wrap system prompt as a cacheable content block (Anthropic prompt caching).
    Schema is ~several KB and stable across requests — caching amortizes the
    token cost across all requests within the 5-minute TTL window."""
    return [{
        "type": "text",
        "text": system_text,
        "cache_control": {"type": "ephemeral"},
    }]

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

        return "\n".join(texts) if texts else "Không có kết quả."
    except Exception as e:
        logger.exception("Tool execution error: %s", name)
        return f"Lỗi khi gọi tool {name}: {e}"


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
        f"[... cắt bớt {remaining:,} ký tự. Gọi lại với limit nhỏ hơn để xem chi tiết.]"
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


def _compact_history(
    messages: list[dict],
    keep_recent_turns: int,
    old_tool_result_chars: int,
) -> list[dict]:
    """Compact prior turns' tool_result payloads while preserving full structure.

    tool_use blocks stay verbatim so the agent still sees which tools were
    called with which args across the whole session — it just doesn't re-read
    the verbose results. Recent turns pass through untouched.
    """
    turns = _split_turns(messages)
    if len(turns) <= keep_recent_turns:
        return messages

    old = turns[:-keep_recent_turns]
    recent = turns[-keep_recent_turns:]

    compacted: list[dict] = []
    for turn in old:
        compacted.extend(_compact_tool_results(turn, old_tool_result_chars))
    for turn in recent:
        compacted.extend(turn)

    logger.info(
        "History compacted: %d turns → kept %d recent, compacted %d old",
        len(turns), len(recent), len(old),
    )
    return compacted


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
    system_prompt = await _build_system_prompt()

    max_result_chars = settings.agent_tool_result_max_chars
    thinking_param = _build_thinking_param()

    claude_messages = _compact_history(
        [{"role": m["role"], "content": m["content"]} for m in messages],
        keep_recent_turns=settings.agent_keep_recent_turns,
        old_tool_result_chars=settings.agent_old_turn_tool_result_chars,
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
            "system": _system_with_cache(system_prompt),
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
