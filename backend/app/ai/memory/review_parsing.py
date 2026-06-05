"""Parsing helpers shared by memory review/consolidation flows."""

import re


def has_api_key(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def strip_code_fence(text: str) -> str:
    """Extract clean JSON from model response text."""
    text = text.strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        return text.rsplit("```", 1)[0].strip()
    match = re.search(r"[\[{]", text)
    if match:
        start = match.start()
        last_close = max(text.rfind("]"), text.rfind("}"))
        if last_close > start:
            return text[start : last_close + 1]
    return text


def extract_text(response) -> str:
    """Return the first text block from an Anthropic-compatible response."""
    for block in response.content:
        text = getattr(block, "text", None)
        block_type = getattr(block, "type", "text")
        if isinstance(text, str) and (
            block_type == "text" or not isinstance(block_type, str)
        ):
            return text
    return ""
