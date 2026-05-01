"""Weekly financial digest — calls MCP tools directly then synthesizes with Sonnet."""

from datetime import datetime, timedelta, timezone

import anthropic

from app.ai.agent.tools import execute_tool
from app.ai.model_registry import get_preferred_model, resolve_client_kwargs
from app.ai.memory.synthesis import get_user_model_text
from app.database import get_session
from app.logging_config import get_logger
from app.models.weekly_digest import WeeklyDigest

logger = get_logger(__name__)

_VN_TZ = timezone(timedelta(hours=7))

_DIGEST_PROMPT = """Based on the financial data above, write a concise weekly financial digest.

Structure (use these headers exactly):

## Tổng quan tháng này
2-3 sentences: income, total spending, savings rate. Compare to last month if data allows.

## Ngân sách
Which categories are over budget, near the limit, or well under. Be specific — name the categories and amounts.

## Mục tiêu
For each active goal: current progress, whether it's on track, and what monthly contribution is needed to hit the deadline.

## Đầu tư
Brief portfolio status: total value, P&L, any notable moves.

## 3 việc cần làm tuần này
A bulleted list of 3 concrete, specific actions — not generic advice. Based on what the data actually shows.

RULES:
- Write in Vietnamese (default) unless the user model is in English
- Use actual numbers from the data — never fabricate
- If a section has no data (e.g., no investments), write "(Không có dữ liệu)" and move on
- Be direct about problems — don't sugarcoat overspending
- Total length: 300-450 words
- Return only the digest text, no preamble
"""

async def generate_digest() -> str:
    """Collect financial data via MCP tools, then synthesize a digest with Sonnet.

    Returns the digest text. Raises on API failure.
    """
    month = datetime.now(_VN_TZ).strftime("%Y-%m")

    # Tools and their exact params — each tool has a different signature.
    tool_calls: list[tuple[str, dict]] = [
        ("get_financial_summary", {"month": month}),
        ("get_budget_status",     {"month": month}),
        ("get_goals",             {}),           # no month param
        ("get_portfolio",         {}),           # no month param
    ]

    # ── Step 1: gather tool data ─────────────────────────────────────────────
    data_sections: list[str] = []
    for tool_name, args in tool_calls:
        try:
            result = await execute_tool(tool_name, args)
            if result and result.strip():
                data_sections.append(f"[{tool_name}]\n{result}")
        except Exception:
            logger.warning("Digest: tool %s failed, skipping", tool_name)

    if not data_sections:
        raise RuntimeError("All financial tools failed — cannot generate digest")

    # ── Step 2: add user model context ───────────────────────────────────────
    user_model = await get_user_model_text()

    prompt_parts: list[str] = []
    if user_model:
        prompt_parts.append(f"<user_model>\n{user_model}\n</user_model>")
    prompt_parts.extend(data_sections)
    prompt_parts.append(_DIGEST_PROMPT)

    # ── Step 3: synthesize with the user's preferred model ────────────────────
    active_model = await get_preferred_model()
    client = anthropic.AsyncAnthropic(**resolve_client_kwargs(active_model))
    response = await client.messages.create(
        model=active_model,
        max_tokens=1500,
        temperature=0.3,
        messages=[{"role": "user", "content": "\n\n".join(prompt_parts)}],
    )

    return response.content[0].text.strip()


async def save_digest(content: str) -> WeeklyDigest:
    """Persist the generated digest and return the saved row."""
    month = datetime.now(_VN_TZ).strftime("%Y-%m")
    async with get_session() as db:
        row = WeeklyDigest(content=content, generated_for_month=month)
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return row


async def get_latest_digest() -> WeeklyDigest | None:
    """Return the most recently generated digest, or None if none exist."""
    from sqlalchemy import select
    async with get_session() as db:
        return (
            await db.execute(
                select(WeeklyDigest).order_by(WeeklyDigest.created_at.desc()).limit(1)
            )
        ).scalar_one_or_none()
