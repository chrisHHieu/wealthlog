"""System prompt builder — stable (cached) + dynamic (uncached) blocks."""

from datetime import datetime, timedelta, timezone

from app.ai.mcp.server import mcp
from app.ai.mcp.tools.discovery import build_schema_summary
from app.ai.memory.episodic import _extract_query_topics, build_summaries_prompt
from app.ai.memory.facts import build_facts_prompt
from app.logging_config import get_logger

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
    "answer questions about earlier conversation history.\n\n"
    "Memory operations:\n"
    "- For listing, editing, forgetting, or verifying stored facts about the "
    "user, use the memory tools (list_my_facts, edit_fact, forget_fact, "
    "verify_fact). Facts marked [✓] in the prompt are user-confirmed; treat "
    "them as ground truth."
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
    return datetime.now(vn_tz).strftime("%A, %d/%m/%Y %H:%M (GMT+7)")


async def build_system_blocks(latest_user_message: str | None = None) -> list[dict]:
    """Build the system prompt as two blocks: stable (cached) + dynamic (uncached).

    The stable block — base instructions, DB schema, MCP resources — is marked
    ``cache_control: ephemeral`` so Anthropic reuses it for 5 minutes. Anything
    that changes per-request (timestamp, summaries, facts) lives in a trailing
    uncached block; otherwise a single fact update or ticking minute would bust
    the cache on the multi-KB schema every turn.

    ``latest_user_message`` lets the episodic block pull older sessions whose
    key topics overlap the current question, on top of the recency-default
    selection. Pass ``None`` (the legacy call shape) to keep recency-only.
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

    query_topics = (
        _extract_query_topics(latest_user_message) if latest_user_message else None
    )
    summaries_block = await build_summaries_prompt(query_topics=query_topics)
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
