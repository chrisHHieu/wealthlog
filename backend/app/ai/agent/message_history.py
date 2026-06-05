"""Helpers for converting persisted chat rows back to provider messages."""

import json

from app.ai.model_registry import get_provider, supports_thinking
from app.models.chat import ChatMessage


def db_rows_to_claude_messages(
    rows: list[ChatMessage],
    active_model: str,
) -> list[dict]:
    """Convert persisted chat rows to Anthropic Messages API format."""
    active_provider = get_provider(active_model)
    model_supports_thinking = supports_thinking(active_model)

    orphaned_tool_ids: set[str] = set()
    messages: list[dict] = []

    for row in rows:
        if row.blocks:
            blocks: list[dict] = row.blocks

            if orphaned_tool_ids and all(b.get("type") == "tool_result" for b in blocks):
                result_ids = {b.get("tool_use_id") for b in blocks}
                if result_ids & orphaned_tool_ids:
                    orphaned_tool_ids -= result_ids
                    continue

            row_provider = get_provider(row.model) if row.model else None
            should_strip = (
                not model_supports_thinking
                or (row_provider is not None and row_provider != active_provider)
            )
            if should_strip:
                for block in blocks:
                    if block.get("type") == "tool_use":
                        orphaned_tool_ids.add(block["id"])
                blocks = [
                    block
                    for block in blocks
                    if block.get("type") not in ("thinking", "tool_use")
                ]
                if not blocks:
                    continue

            messages.append({"role": row.role, "content": blocks})
        elif row.content:
            messages.append({"role": row.role, "content": row.content})

    return messages


def parse_sse(event: str) -> tuple[str, dict]:
    """Extract (event_name, data) from an SSE-formatted string."""
    name = ""
    data: dict = {}
    for line in event.split("\n"):
        if line.startswith("event: "):
            name = line[7:].strip()
        elif line.startswith("data: "):
            try:
                data = json.loads(line[6:])
            except json.JSONDecodeError:
                data = {}
    return name, data
