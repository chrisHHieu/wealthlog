"""Main agent loop — orchestrates Claude streaming + MCP tool execution."""

import asyncio
import json
import uuid
from collections.abc import AsyncGenerator

import anthropic

from app.ai.model_registry import get_preferred_model, resolve_client_kwargs, supports_thinking

from app.ai.agent.compaction import _compact_history, _truncate_tool_result
from app.ai.agent.prompt import build_system_blocks
from app.ai.agent.streaming import (
    EVENT_DONE,
    EVENT_ITERATION,
    EVENT_PERSIST_ASSISTANT,
    EVENT_PERSIST_TOOL_RESULTS,
    EVENT_TEXT_DELTA,
    EVENT_TEXT_START,
    EVENT_TEXT_STOP,
    EVENT_THINKING_DELTA,
    EVENT_THINKING_START,
    EVENT_THINKING_STOP,
    EVENT_TOOL_DONE,
    EVENT_TOOL_INPUT,
    EVENT_TOOL_START,
    sse_event,
)
from app.ai.agent.token_budget import estimate_request_tokens
from app.ai.agent.tools import MAX_ITERATIONS, execute_tool, get_tools_for_claude
from app.ai.memory.episodic import summarize_session
from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


def _build_thinking_param(model: str) -> dict | None:
    """Return thinking config if the model supports it and thinking is enabled."""
    if not settings.agent_thinking_enabled or not supports_thinking(model):
        return None
    return {"type": "enabled", "budget_tokens": settings.agent_thinking_budget}


async def run_agent_stream(
    messages: list[dict],
    session_id: uuid.UUID | None = None,
    model: str | None = None,
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
    active_model = model or await get_preferred_model()
    client = anthropic.AsyncAnthropic(**resolve_client_kwargs(active_model))
    tools = await get_tools_for_claude()
    # Walk the tail to find the most recent user *text* — tool_result rows
    # also carry role="user" but their content is structured blocks, not the
    # natural-language string we want to tokenize for episodic retrieval.
    latest_user = next(
        (
            m["content"] for m in reversed(messages)
            if m["role"] == "user" and isinstance(m["content"], str)
        ),
        None,
    )
    system_blocks = await build_system_blocks(latest_user_message=latest_user)

    max_result_chars = settings.agent_tool_result_max_chars
    thinking_param = _build_thinking_param(active_model)

    async def _run_tool(tu: dict) -> tuple[dict, str, bool]:
        """Execute one tool call in parallel; return (tu, result_text, is_error)."""
        try:
            inp = json.loads(tu["input_json"]) if tu["input_json"] else {}
        except json.JSONDecodeError:
            inp = {}
        text, is_error = await execute_tool(tu["name"], inp)
        return tu, _truncate_tool_result(text, max_result_chars), is_error

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
        client, active_model, system_blocks, claude_messages, tools,
    )
    if est_tokens is not None:
        logger.info("Pre-send input tokens: %d", est_tokens)
        if est_tokens > settings.agent_max_input_tokens:
            logger.warning(
                "Input tokens %d exceed soft budget %d — context may be unhealthy",
                est_tokens, settings.agent_max_input_tokens,
            )

    accumulated_result_chars = 0  # tracks tool result chars added after initial estimate

    for iteration in range(MAX_ITERATIONS):
        logger.info("Agent iteration %d", iteration + 1)
        yield sse_event(EVENT_ITERATION, {"n": iteration + 1})

        # Track all content blocks in order — needed for proper assistant history
        # and for preserving thinking signatures required by the API.
        blocks: list[dict] = []  # each: {index, type, ...block-specific}
        stop_reason = None
        usage = {"input": 0, "cache_read": 0, "cache_write": 0, "output": 0}

        # When thinking is active, Anthropic requires max_tokens > budget_tokens.
        # Ensure this invariant regardless of what's configured in .env.
        effective_max_tokens = settings.agent_max_tokens
        if thinking_param:
            effective_max_tokens = max(
                effective_max_tokens,
                thinking_param["budget_tokens"] + 1024,
            )

        stream_kwargs: dict = {
            "model": active_model,
            "max_tokens": effective_max_tokens,
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
                        yield sse_event(EVENT_THINKING_START, {"step_id": step_id})

                    elif block.type == "text":
                        blocks.append({
                            "index": idx,
                            "type": "text",
                            "step_id": step_id,
                            "text": "",
                        })
                        yield sse_event(EVENT_TEXT_START, {"step_id": step_id})

                    elif block.type == "tool_use":
                        blocks.append({
                            "index": idx,
                            "type": "tool_use",
                            "step_id": step_id,
                            "id": block.id,
                            "name": block.name,
                            "input_json": "",
                        })
                        yield sse_event(EVENT_TOOL_START, {
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
                        yield sse_event(EVENT_TEXT_DELTA, {
                            "step_id": block["step_id"],
                            "text": event.delta.text,
                        })
                    elif event.delta.type == "thinking_delta":
                        block["thinking"] += event.delta.thinking
                        yield sse_event(EVENT_THINKING_DELTA, {
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
                        yield sse_event(EVENT_THINKING_STOP, {"step_id": block["step_id"]})
                    elif block["type"] == "text":
                        # "final" flag will be set correctly based on stop_reason below,
                        # but emit provisional stop for UI to finalize the text block
                        yield sse_event(EVENT_TEXT_STOP, {
                            "step_id": block["step_id"],
                            "final": False,  # updated on done if no more tools
                        })
                    elif block["type"] == "tool_use":
                        try:
                            inp = json.loads(block["input_json"]) if block["input_json"] else {}
                        except json.JSONDecodeError:
                            inp = {}
                        yield sse_event(EVENT_TOOL_INPUT, {
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
        yield sse_event(EVENT_PERSIST_ASSISTANT, {"blocks": assistant_content})

        # If no tool calls, this is the final answer — we're done
        if stop_reason != "tool_use" or not tool_uses:
            break

        claude_messages.append({"role": "assistant", "content": assistant_content})

        # Execute all tool calls in parallel — Claude emits them as a batch,
        # and they're independent DB reads so there's no reason to serialize.
        tool_outputs: list[tuple[dict, str, bool]] = await asyncio.gather(
            *[_run_tool(tu) for tu in tool_uses]
        )

        tool_results = []
        for tu, result_text, is_error in tool_outputs:
            entry: dict = {
                "type": "tool_result",
                "tool_use_id": tu["id"],
                "content": result_text,
            }
            if is_error:
                entry["is_error"] = True
            tool_results.append(entry)

            yield sse_event(EVENT_TOOL_DONE, {
                "step_id": tu["step_id"],
                "id": tu["id"],
                "result": result_text,
                "is_error": is_error,
            })

        # Mid-loop token budget check — rough estimate (4 chars ≈ 1 token).
        # The initial estimate only covers the pre-send shape; tool results
        # added across iterations can push us well past the soft budget.
        accumulated_result_chars += sum(len(r) for _, r, _ in tool_outputs)
        if est_tokens is not None:
            mid_est = est_tokens + accumulated_result_chars // 4
            if mid_est > settings.agent_max_input_tokens:
                logger.warning(
                    "Mid-loop token estimate ~%d exceeds budget %d (iter=%d)",
                    mid_est, settings.agent_max_input_tokens, iteration + 1,
                )

        claude_messages.append({"role": "user", "content": tool_results})
        yield sse_event(EVENT_PERSIST_TOOL_RESULTS, {"blocks": tool_results})

    else:
        # MAX_ITERATIONS exhausted — agent was still in tool-calling mode.
        logger.warning("Agent hit MAX_ITERATIONS (%d) without finishing", MAX_ITERATIONS)
        fallback = (
            "Tôi đã thực hiện nhiều bước nhưng chưa hoàn thành được yêu cầu. "
            "Vui lòng thử câu hỏi cụ thể hơn hoặc chia nhỏ yêu cầu."
        )
        yield sse_event(EVENT_TEXT_START, {"step_id": "fallback"})
        yield sse_event(EVENT_TEXT_DELTA, {"step_id": "fallback", "text": fallback})
        yield sse_event(EVENT_TEXT_STOP, {"step_id": "fallback", "final": True})
        yield sse_event(EVENT_PERSIST_ASSISTANT, {
            "blocks": [{"type": "text", "text": fallback}]
        })

    yield sse_event(EVENT_DONE, {})
