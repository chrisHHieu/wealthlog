"""Pre-send token accounting — surfaces runaway sessions before they 400."""

from anthropic import AsyncAnthropic

from app.logging_config import get_logger

logger = get_logger(__name__)


async def estimate_request_tokens(
    client: AsyncAnthropic,
    model: str,
    system: list[dict] | str,
    messages: list[dict],
    tools: list[dict] | None = None,
) -> int | None:
    """Count input tokens for the request before sending.

    Uses Anthropic's free ``count_tokens`` endpoint. Returns ``None`` on
    failure so callers proceed blind rather than block on transient errors.
    """
    try:
        # DeepSeek's Anthropic-compat endpoint doesn't properly support count_tokens
        # (requires max_tokens, but the Anthropic SDK doesn't accept it there).
        if model.startswith("deepseek-"):
            return None
        kwargs: dict = {"model": model, "system": system, "messages": messages}
        if tools:
            kwargs["tools"] = tools
        resp = await client.messages.count_tokens(**kwargs)
        return resp.input_tokens
    except Exception:
        logger.warning("count_tokens call failed", exc_info=True)
        return None
