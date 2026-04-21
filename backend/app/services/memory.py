"""Long-term memory service — user facts + background review agent."""

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta

import anthropic
from sqlalchemy import func, nulls_last, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.logging_config import get_logger
from app.mcp.db import get_session
from app.models.chat import ChatMessage
from app.models.user_fact import UserFact

logger = get_logger(__name__)

# ── User Facts CRUD ──────────────────────────────────────────────────────────


async def _bump_access(db: AsyncSession, ids: list) -> None:
    """Record that the given facts were just surfaced to the prompt.

    Runs as a set-based UPDATE so retrieval cost stays O(1) regardless of
    the number of facts returned.
    """
    if not ids:
        return
    await db.execute(
        update(UserFact)
        .where(UserFact.id.in_(ids))
        .values(
            access_count=UserFact.access_count + 1,
            last_accessed_at=datetime.now(UTC),
        )
    )


async def get_user_facts(limit: int = 20, track_access: bool = True) -> list[dict]:
    """Load non-expired user facts for system prompt injection.

    Ordered by importance first (reviewer-assigned), then by recent usage
    so frequently-surfaced facts bubble up among equals, then by freshness.
    When `track_access` is on, bumps access_count and last_accessed_at for
    the rows returned — disable it for read-only introspection.
    """
    now = datetime.now(UTC)
    async with get_session() as db:
        rows = (
            await db.execute(
                select(UserFact)
                .where(
                    or_(
                        UserFact.expires_at.is_(None),
                        UserFact.expires_at > now,
                    ),
                )
                .order_by(
                    UserFact.importance.desc(),
                    nulls_last(UserFact.last_accessed_at.desc()),
                    UserFact.updated_at.desc(),
                )
                .limit(limit)
            )
        ).scalars().all()

        if track_access:
            await _bump_access(db, [r.id for r in rows])

        return [
            {"fact": r.fact, "category": r.category, "importance": r.importance}
            for r in rows
        ]


async def save_user_fact(
    fact: str,
    category: str = "general",
    source_session_id: str | None = None,
    expires_at: datetime | None = None,
    importance: int = 5,
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
            expires_at=expires_at,
            importance=importance,
        )
        db.add(new_fact)
        return {"status": "saved", "fact": fact, "category": category}


async def update_user_fact(
    fact_id: uuid.UUID,
    fact: str,
    category: str,
    importance: int,
    expires_at: datetime | None,
) -> bool:
    """Replace an existing fact in-place.

    Preserves id, created_at and access stats so the fact's history stays
    continuous — used by the review agent when Haiku judges a new
    observation to be a refinement of an existing fact rather than net-new.
    """
    async with get_session() as db:
        result = await db.execute(
            select(UserFact).where(UserFact.id == fact_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return False
        row.fact = fact
        row.category = category
        row.importance = importance
        row.expires_at = expires_at
        return True


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
        "preference": "Preference",
        "habit": "Habit",
        "goal": "Goal",
        "context": "Context",
        "general": "General",
    }

    lines = ["[Known facts about the user]"]
    for f in facts:
        label = category_labels.get(f["category"], f["category"])
        lines.append(f"- ({label}) {f['fact']}")
    lines.append("[End of user facts]")

    return "\n".join(lines)


# ── Background Review Agent ──────────────────────────────────────────────────

_REVIEW_PROMPT = (
    "Read the personal-finance conversation above between the user and AI.\n\n"
    "Find memorable facts about the user:\n"
    "1. Financial habits (e.g., 'forgets to log cash', 'salary paid on the 15th')\n"
    "2. Preferences (e.g., 'prefers weekly reports')\n"
    "3. Goals (e.g., 'saving 50M for a car', 'paying off debt')\n"
    "4. Personal context (e.g., 'spouse manages separate finances', 'student')\n\n"
    "RULES:\n"
    "- Return a JSON array. Each item has:\n"
    "  - 'action': 'add' (new fact) or 'replace' (update an existing fact)\n"
    "  - 'fact', 'category', 'importance', 'expires_in_days' (optional)\n"
    "  - If action='replace', include 'replaces': 1-based index from 'Known facts' list\n"
    "- Use 'replace' when the new fact refines/supersedes an existing one\n"
    "  (e.g., savings goal raised from 50M to 80M → replace old goal, merge info).\n"
    "- Use 'add' for a new topic not covered by any existing fact.\n"
    "- If info already exists in known facts and has NOT changed, omit it.\n"
    "- Each fact must be one short sentence.\n"
    "- Write the fact text in the SAME LANGUAGE as the conversation above.\n"
    "- If nothing new is found, return []\n\n"
    "category: preference | habit | goal | context | general\n"
    "importance: 1-10 (9-10 core; 6-8 frequently useful; 3-5 supplementary; 1-2 incidental)\n"
    "expires_in_days: null = evergreen. E.g. 'currently a student' → 365, 'dieting this month' → 30\n\n"
    "Return ONLY JSON, no explanation.\n"
    "Example:\n"
    "[\n"
    "  {\"action\": \"add\", \"fact\": \"Has 2 young children\", \"category\": \"context\", \"importance\": 7},\n"
    "  {\"action\": \"replace\", \"replaces\": 3, \"fact\": \"Savings goal: 80M (raised from 50M)\",\n"
    "   \"category\": \"goal\", \"importance\": 9}\n"
    "]"
)


_VALID_CATEGORIES = ("preference", "habit", "goal", "context", "general")
_DEFAULT_IMPORTANCE = 5


def _clamp_importance(raw: object) -> int:
    """Coerce the reviewer's importance hint into the 1-10 band.

    Malformed or missing values fall back to the neutral default so one bad
    LLM response doesn't poison ordering for the rest of the facts.
    """
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return _DEFAULT_IMPORTANCE
    value = int(raw)
    if value < 1:
        return 1
    if value > 10:
        return 10
    return value


def _compute_expiry(item: dict, category: str) -> datetime | None:
    """Translate the reviewer's 'expires_in_days' hint into an absolute datetime.

    Defaults to the configured fallback TTL only for 'context' facts — the
    most common source of time-bound info (roles, life stages). Other
    categories stay evergreen unless the reviewer says otherwise.
    """
    raw = item.get("expires_in_days")
    days: float | None = None
    if isinstance(raw, (int, float)) and raw > 0:
        days = float(raw)
    elif raw is None and category == "context":
        days = float(settings.user_fact_default_context_ttl_days)
    if days is None:
        return None
    return datetime.now(UTC) + timedelta(days=days)


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


async def _load_existing_for_review() -> list[tuple[uuid.UUID, str]]:
    """Load (id, fact) pairs of non-expired facts for dedup matching.

    Used only by the review agent — returns ids so the reviewer's 'replace'
    action can be mapped back to concrete rows. Access stats are not bumped
    here since these rows aren't being surfaced to the primary agent.
    """
    async with get_session() as db:
        rows = (
            await db.execute(
                select(UserFact.id, UserFact.fact)
                .where(
                    or_(
                        UserFact.expires_at.is_(None),
                        UserFact.expires_at > datetime.now(UTC),
                    ),
                )
                .order_by(UserFact.updated_at.desc())
                .limit(50)
            )
        ).all()
        return [(row[0], row[1]) for row in rows]


def _strip_code_fence(text: str) -> str:
    """Remove a leading ```json ... ``` wrapper if Haiku added one."""
    text = text.strip()
    if not text.startswith("```"):
        return text
    text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    return text.rsplit("```", 1)[0].strip()


async def _apply_review_item(
    item: dict,
    existing: list[tuple[uuid.UUID, str]],
    session_id: uuid.UUID,
) -> str:
    """Route one reviewer item to add/update and return the outcome tag.

    Outcomes: 'saved', 'updated', 'duplicate', 'skipped'. Kept as strings
    so the caller can log counts without caring about internal details.
    """
    fact_text = item.get("fact", "").strip()
    if not fact_text:
        return "skipped"

    category = item.get("category", "general")
    if category not in _VALID_CATEGORIES:
        category = "general"

    importance = _clamp_importance(item.get("importance"))
    expires_at = _compute_expiry(item, category)

    if item.get("action") == "replace":
        idx = item.get("replaces")
        if isinstance(idx, int) and 1 <= idx <= len(existing):
            fact_id, _ = existing[idx - 1]
            ok = await update_user_fact(
                fact_id=fact_id,
                fact=fact_text,
                category=category,
                importance=importance,
                expires_at=expires_at,
            )
            return "updated" if ok else "skipped"
        # Invalid replaces index → fall through to add so the insight isn't lost

    result = await save_user_fact(
        fact=fact_text,
        category=category,
        source_session_id=str(session_id),
        expires_at=expires_at,
        importance=importance,
    )
    return result["status"]  # 'saved' or 'duplicate'


async def _run_review(
    session_id: uuid.UUID,
    messages: list[dict],
) -> None:
    """Background task: use Claude to extract or refine user facts.

    Sends conversation + numbered list of existing facts to Haiku, which
    returns add/replace actions. Routing and dedup live in
    :func:`_apply_review_item`.
    """
    if not settings.anthropic_api_key:
        return

    try:
        logger.info("Background review started for session %s", session_id)

        existing = await _load_existing_for_review()

        review_messages = [
            {
                "role": m["role"],
                "content": m["content"] if isinstance(m["content"], str) else str(m["content"]),
            }
            for m in messages
        ]

        if existing:
            numbered = "\n".join(f"{i + 1}. {fact}" for i, (_, fact) in enumerate(existing))
            facts_context = f"Facts đã biết:\n{numbered}"
            review_messages.append({
                "role": "user",
                "content": f"{facts_context}\n\n{_REVIEW_PROMPT}",
            })
        else:
            review_messages.append({"role": "user", "content": _REVIEW_PROMPT})

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=settings.agent_review_model,
            max_tokens=1024,
            temperature=0.3,
            messages=review_messages,
        )

        items = json.loads(_strip_code_fence(response.content[0].text))

        if not isinstance(items, list) or not items:
            logger.info("Background review: no actions returned")
            return

        counts = {"saved": 0, "updated": 0, "duplicate": 0, "skipped": 0}
        for item in items:
            if not isinstance(item, dict):
                counts["skipped"] += 1
                continue
            outcome = await _apply_review_item(item, existing, session_id)
            counts[outcome] = counts.get(outcome, 0) + 1

        logger.info(
            "Background review done for %s — added=%d updated=%d dup=%d skipped=%d",
            session_id,
            counts["saved"], counts["updated"], counts["duplicate"], counts["skipped"],
        )

    except json.JSONDecodeError:
        logger.warning("Background review: failed to parse JSON response")
    except Exception:
        logger.exception("Background review failed for session %s", session_id)
