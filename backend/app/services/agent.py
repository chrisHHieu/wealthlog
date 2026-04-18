"""AI Agent service — connects Claude API to MCP tools."""

import json
from collections.abc import AsyncGenerator
from datetime import datetime, timezone, timedelta

import anthropic

from app.config import settings
from app.logging_config import get_logger
from app.mcp.server import mcp
from app.services.memory import build_facts_prompt

logger = get_logger(__name__)

_SYSTEM_BASE = (
    "Bạn là WealthLog AI — trợ lý tài chính cá nhân thông minh. "
    "Bạn giúp người dùng quản lý thu chi, ngân sách, mục tiêu tiết kiệm và đầu tư.\n\n"
    "Quy tắc:\n"
    "- Luôn dùng tool để lấy dữ liệu thực, KHÔNG bịa số liệu\n"
    "- Tiền tệ mặc định: VND. Format số: dùng dấu phẩy (ví dụ: 1,000,000)\n"
    "- Format tháng: YYYY-MM. Format ngày: YYYY-MM-DD\n"
    "- Trả lời ngắn gọn, rõ ràng, có insight\n"
    "- Khi user hỏi tổng quan, gọi nhiều tool để có bức tranh đầy đủ\n"
    "- Đưa ra lời khuyên cụ thể khi phù hợp\n"
    "- Khi tạo giao dịch, dùng đúng category_name từ danh sách bên dưới"
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
    """Build system prompt with live MCP resources and user facts injected."""
    sections = [f"Thời gian hiện tại: {_now_vn()}\n\n{_SYSTEM_BASE}"]

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

    # Keep the beginning (most important) and add a truncation notice
    cut = max_chars - 80  # reserve space for the notice
    truncated = text[:cut]

    # Try to cut at a newline boundary to avoid broken lines
    last_newline = truncated.rfind("\n")
    if last_newline > cut * 0.7:
        truncated = truncated[:last_newline]

    remaining = len(text) - len(truncated)
    return (
        f"{truncated}\n\n"
        f"[... cắt bớt {remaining:,} ký tự. Gọi lại với limit nhỏ hơn để xem chi tiết.]"
    )


def _compact_old_tool_results(messages: list[dict], keep_recent: int = 2) -> list[dict]:
    """Replace verbose tool results from older turns with compact summaries.

    Within the agent loop, tool results accumulate across iterations.
    Old results (beyond keep_recent iterations) are compacted to save tokens.
    The assistant already processed them, so the full text is no longer needed.
    """
    # Find indices of user messages that contain tool_results
    tool_result_indices = []
    for i, msg in enumerate(messages):
        if msg["role"] == "user" and isinstance(msg.get("content"), list):
            if any(
                isinstance(block, dict) and block.get("type") == "tool_result"
                for block in msg["content"]
            ):
                tool_result_indices.append(i)

    # Nothing to compact
    if len(tool_result_indices) <= keep_recent:
        return messages

    # Compact all but the most recent tool-result messages
    indices_to_compact = set(tool_result_indices[:-keep_recent])
    compacted = []

    for i, msg in enumerate(messages):
        if i not in indices_to_compact:
            compacted.append(msg)
            continue

        # Replace each tool_result content with a short summary
        new_content = []
        for block in msg["content"]:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                original = block.get("content", "")
                # Extract first line as a hint of what the result was
                first_line = original.split("\n", 1)[0][:100] if original else ""
                new_content.append({
                    "type": "tool_result",
                    "tool_use_id": block["tool_use_id"],
                    "content": f"[Kết quả đã xử lý: {first_line}...]",
                })
            else:
                new_content.append(block)

        compacted.append({"role": "user", "content": new_content})

    return compacted


async def _count_tokens(
    client: anthropic.AsyncAnthropic,
    messages: list[dict],
    system: str = "",
    tools: list[dict] | None = None,
) -> int:
    """Count tokens using Anthropic's official API — exact count."""
    kwargs: dict = {
        "model": settings.agent_model,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools
    result = await client.messages.count_tokens(**kwargs)
    return result.input_tokens


async def _compress_history(
    client: anthropic.AsyncAnthropic,
    messages: list[dict],
    max_tokens: int,
    system: str = "",
    tools: list[dict] | None = None,
    keep_recent: int = 6,
) -> list[dict]:
    """Compress conversation history when it exceeds token budget.

    Uses Anthropic count_tokens API for exact measurement.
    Strategy:
    1. Always keep the most recent `keep_recent` messages intact
    2. Older messages are condensed into a summary block
    """
    if len(messages) <= keep_recent:
        return messages

    total = await _count_tokens(client, messages, system, tools)
    if total <= max_tokens:
        return messages

    logger.info(
        "History compression: %d tokens > %d budget, %d messages — compressing",
        total, max_tokens, len(messages),
    )

    # Split: old messages to compress, recent messages to keep
    old = messages[:-keep_recent]
    recent = messages[-keep_recent:]

    # Extract key points from old turns
    summary_parts = []
    for msg in old:
        role = msg["role"]
        content = msg.get("content", "")
        if isinstance(content, str) and content.strip():
            snippet = content[:150].strip()
            if len(content) > 150:
                snippet += "..."
            prefix = "User" if role == "user" else "AI"
            summary_parts.append(f"- {prefix}: {snippet}")

    if not summary_parts:
        return messages

    summary_text = (
        "[Tóm tắt cuộc trò chuyện trước đó]\n"
        + "\n".join(summary_parts)
        + "\n[Hết tóm tắt — cuộc trò chuyện tiếp tục bên dưới]"
    )

    compressed = [{"role": "user", "content": summary_text}]

    # Ensure valid alternation: if recent starts with "user", we need an assistant response after summary
    if recent and recent[0]["role"] == "user":
        compressed.append({"role": "assistant", "content": "Đã hiểu context trước đó. Tiếp tục hỗ trợ."})

    compressed.extend(recent)

    new_total = await _count_tokens(client, compressed, system, tools)
    logger.info(
        "History compressed: %d → %d tokens (%d%% reduction)",
        total, new_total, round((1 - new_total / total) * 100),
    )

    return compressed


# SSE event types
EVENT_TOOL_START = "tool_start"
EVENT_TOOL_DONE = "tool_done"
EVENT_TEXT_DELTA = "text_delta"
EVENT_DONE = "done"
EVENT_ERROR = "error"


def _sse_event(event: str, data: dict) -> str:
    """Format an SSE event string."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def run_agent_stream(
    messages: list[dict],
) -> AsyncGenerator[str, None]:
    """Run the agent loop, yielding SSE events.

    Events:
    - tool_start: {"name": "tool_name"}
    - tool_done:  {"name": "tool_name", "result": "..."}
    - text_delta: {"text": "..."}
    - done:       {}
    - error:      {"message": "..."}
    """
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    tools = await _get_tools_for_claude()
    system_prompt = await _build_system_prompt()

    max_result_chars = settings.agent_tool_result_max_chars

    # Build message history for Claude, compressing if too long
    claude_messages = []
    for msg in messages:
        claude_messages.append({
            "role": msg["role"],
            "content": msg["content"],
        })
    claude_messages = await _compress_history(
        client, claude_messages, settings.agent_max_history_tokens,
        system=system_prompt, tools=tools,
    )

    for iteration in range(MAX_ITERATIONS):
        logger.info("Agent iteration %d", iteration + 1)

        # Compact old tool results to save tokens before calling Claude
        if iteration >= 3:
            claude_messages = _compact_old_tool_results(claude_messages)

        # Stream Claude response
        collected_text = ""
        tool_uses = []
        stop_reason = None

        async with client.messages.stream(
            model=settings.agent_model,
            max_tokens=settings.agent_max_tokens,
            system=system_prompt,
            messages=claude_messages,
            tools=tools,
        ) as stream:
            async for event in stream:
                if event.type == "content_block_start":
                    if event.content_block.type == "tool_use":
                        tool_uses.append({
                            "id": event.content_block.id,
                            "name": event.content_block.name,
                            "input_json": "",
                        })
                        yield _sse_event(EVENT_TOOL_START, {
                            "name": event.content_block.name,
                        })

                elif event.type == "content_block_delta":
                    if event.delta.type == "text_delta":
                        collected_text += event.delta.text
                        yield _sse_event(EVENT_TEXT_DELTA, {
                            "text": event.delta.text,
                        })
                    elif event.delta.type == "input_json_delta":
                        if tool_uses:
                            tool_uses[-1]["input_json"] += event.delta.partial_json

                elif event.type == "message_delta":
                    stop_reason = event.delta.stop_reason

        # If no tool calls, we're done
        if stop_reason != "tool_use" or not tool_uses:
            break

        # Build the assistant message content for Claude's history
        assistant_content = []
        if collected_text:
            assistant_content.append({"type": "text", "text": collected_text})
        for tu in tool_uses:
            try:
                input_data = json.loads(tu["input_json"]) if tu["input_json"] else {}
            except json.JSONDecodeError:
                input_data = {}
            assistant_content.append({
                "type": "tool_use",
                "id": tu["id"],
                "name": tu["name"],
                "input": input_data,
            })

        claude_messages.append({"role": "assistant", "content": assistant_content})

        # Execute all tool calls and send results back
        tool_results = []
        for tu in tool_uses:
            try:
                input_data = json.loads(tu["input_json"]) if tu["input_json"] else {}
            except json.JSONDecodeError:
                input_data = {}

            result_text = await _execute_tool(tu["name"], input_data)

            # Truncate oversized tool results
            result_text = _truncate_tool_result(result_text, max_result_chars)

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu["id"],
                "content": result_text,
            })

            yield _sse_event(EVENT_TOOL_DONE, {
                "name": tu["name"],
                "result": result_text[:200],  # truncate for SSE
            })

        claude_messages.append({"role": "user", "content": tool_results})

        # Reset for next iteration
        collected_text = ""
        tool_uses = []

    yield _sse_event(EVENT_DONE, {})
