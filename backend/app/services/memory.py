"""Long-term memory service — user facts + background review agent."""

import asyncio
import json
import uuid

import anthropic
from sqlalchemy import func, select

from app.config import settings
from app.logging_config import get_logger
from app.mcp.db import get_session
from app.models.chat import ChatMessage
from app.models.user_fact import UserFact

logger = get_logger(__name__)

# ── User Facts CRUD ──────────────────────────────────────────────────────────


async def get_user_facts(limit: int = 20) -> list[dict]:
    """Load user facts for system prompt injection."""
    async with get_session() as db:
        rows = (
            await db.execute(
                select(UserFact)
                .order_by(UserFact.updated_at.desc())
                .limit(limit)
            )
        ).scalars().all()

        return [
            {"fact": r.fact, "category": r.category}
            for r in rows
        ]


async def save_user_fact(
    fact: str,
    category: str = "general",
    source_session_id: str | None = None,
) -> dict:
    """Save a new user fact, deduplicating against existing facts."""
    async with get_session() as db:
        # Check for near-duplicate (exact match)
        existing = await db.execute(
            select(UserFact).where(UserFact.fact == fact)
        )
        if existing.scalar_one_or_none():
            return {"status": "duplicate", "fact": fact}

        new_fact = UserFact(
            fact=fact,
            category=category,
            source_session_id=source_session_id,
        )
        db.add(new_fact)
        return {"status": "saved", "fact": fact, "category": category}


async def delete_user_fact(fact_id: uuid.UUID) -> bool:
    """Delete a user fact by ID."""
    async with get_session() as db:
        result = await db.execute(
            select(UserFact).where(UserFact.id == fact_id)
        )
        fact = result.scalar_one_or_none()
        if fact:
            await db.delete(fact)
            return True
        return False


async def build_facts_prompt() -> str:
    """Build a text block of user facts for system prompt injection."""
    facts = await get_user_facts()
    if not facts:
        return ""

    category_labels = {
        "preference": "Sở thích",
        "habit": "Thói quen",
        "goal": "Mục tiêu",
        "context": "Ngữ cảnh",
        "general": "Chung",
    }

    lines = ["[Thông tin đã biết về người dùng]"]
    for f in facts:
        label = category_labels.get(f["category"], f["category"])
        lines.append(f"- ({label}) {f['fact']}")
    lines.append("[Hết thông tin người dùng]")

    return "\n".join(lines)


# ── Background Review Agent ──────────────────────────────────────────────────

_REVIEW_PROMPT = (
    "Đọc lại cuộc hội thoại ở trên giữa user và AI về tài chính cá nhân.\n\n"
    "Tìm những thông tin đáng nhớ về user:\n"
    "1. Thói quen tài chính (ví dụ: 'hay quên ghi tiền mặt', 'trả lương ngày 15')\n"
    "2. Sở thích (ví dụ: 'thích xem báo cáo theo tuần', 'không dùng thẻ tín dụng')\n"
    "3. Mục tiêu (ví dụ: 'muốn tiết kiệm 50tr mua xe', 'đang trả nợ')\n"
    "4. Ngữ cảnh cá nhân (ví dụ: 'vợ quản chi riêng', 'sinh viên')\n\n"
    "QUAN TRỌNG:\n"
    "- Chỉ trích xuất facts MỚI, không lặp lại facts đã biết\n"
    "- Mỗi fact phải ngắn gọn (1 câu)\n"
    "- Trả về JSON array, mỗi item có 'fact' và 'category'\n"
    "- category: preference | habit | goal | context | general\n"
    "- Nếu không có gì mới đáng nhớ, trả về []\n\n"
    "Trả lời CHỈ bằng JSON array, không giải thích thêm.\n"
    "Ví dụ: [{\"fact\": \"Lương ngày 15 hàng tháng\", \"category\": \"context\"}]"
)


async def maybe_trigger_review(
    session_id: uuid.UUID,
    messages: list[dict],
) -> None:
    """Fire a background fact-extraction review every N user turns.

    Turn count is derived from the DB (non-empty user-role messages =
    real user turns, excluding tool_result rows), so process restarts
    don't reset the cadence.
    """
    async with get_session() as db:
        result = await db.execute(
            select(func.count(ChatMessage.id)).where(
                ChatMessage.session_id == session_id,
                ChatMessage.role == "user",
                ChatMessage.content != "",
            )
        )
        turn_count = result.scalar_one()

    if turn_count == 0 or turn_count % settings.agent_review_cadence != 0:
        return

    asyncio.create_task(_run_review(session_id, messages))


async def _run_review(
    session_id: uuid.UUID,
    messages: list[dict],
) -> None:
    """Background task: use Claude to extract user facts from conversation."""
    if not settings.anthropic_api_key:
        return

    try:
        logger.info("Background review started for session %s", session_id)

        # Load existing facts to avoid duplicates
        existing_facts = await get_user_facts(limit=50)
        existing_texts = {f["fact"] for f in existing_facts}

        # Build review messages
        review_messages = []
        for m in messages:
            review_messages.append({
                "role": m["role"],
                "content": m["content"] if isinstance(m["content"], str) else str(m["content"]),
            })

        # Add existing facts context
        if existing_texts:
            facts_context = "Facts đã biết (KHÔNG lặp lại):\n" + "\n".join(
                f"- {f}" for f in existing_texts
            )
            review_messages.append({
                "role": "user",
                "content": f"{facts_context}\n\n{_REVIEW_PROMPT}",
            })
        else:
            review_messages.append({
                "role": "user",
                "content": _REVIEW_PROMPT,
            })

        # Call Claude Haiku (cheap, fast)
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=settings.agent_review_model,
            max_tokens=1024,
            temperature=0.3,
            messages=review_messages,
        )

        # Parse response
        text = response.content[0].text.strip()

        # Handle markdown code blocks
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
            text = text.strip()

        facts = json.loads(text)

        if not isinstance(facts, list) or not facts:
            logger.info("Background review: no new facts found")
            return

        saved_count = 0
        for item in facts:
            if not isinstance(item, dict):
                continue
            fact_text = item.get("fact", "").strip()
            category = item.get("category", "general")

            if not fact_text or fact_text in existing_texts:
                continue

            if category not in ("preference", "habit", "goal", "context", "general"):
                category = "general"

            result = await save_user_fact(
                fact=fact_text,
                category=category,
                source_session_id=str(session_id),
            )
            if result["status"] == "saved":
                saved_count += 1

        logger.info(
            "Background review completed: %d new facts saved for session %s",
            saved_count, session_id,
        )

    except json.JSONDecodeError:
        logger.warning("Background review: failed to parse JSON response")
    except Exception:
        logger.exception("Background review failed for session %s", session_id)
