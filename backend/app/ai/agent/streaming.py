"""SSE event names + encoder for the agent stream."""

import json

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


def sse_event(event: str, data: dict) -> str:
    """Format an SSE event string."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
