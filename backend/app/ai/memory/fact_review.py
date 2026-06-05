"""Review-agent helpers for loading and applying user fact updates."""

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy import or_, select

from app.models.user_fact import UserFact

SaveFact = Callable[..., Awaitable[dict]]
UpdateFact = Callable[..., Awaitable[bool]]


async def load_existing_for_review(session_factory) -> list[tuple[uuid.UUID, str]]:
    """Load non-expired fact ids and text for review-agent dedup routing."""
    async with session_factory() as db:
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


async def apply_review_item(
    item: dict,
    existing: list[tuple[uuid.UUID, str]],
    session_id: uuid.UUID,
    valid_categories: tuple[str, ...],
    clamp_importance,
    clamp_confidence,
    compute_expiry,
    normalize_topics,
    save_fact: SaveFact,
    update_fact: UpdateFact,
) -> str:
    """Route one reviewer item to add/update and return the outcome tag."""
    fact_text = item.get("fact", "").strip()
    if not fact_text:
        return "skipped"

    category = item.get("category", "general")
    if category not in valid_categories:
        category = "general"

    importance = clamp_importance(item.get("importance"))
    confidence = clamp_confidence(item.get("confidence"))
    expires_at = compute_expiry(item, category)
    topics = normalize_topics(item.get("topics"), category)

    if item.get("action") == "replace":
        idx = item.get("replaces")
        if isinstance(idx, int) and 1 <= idx <= len(existing):
            fact_id, _ = existing[idx - 1]
            ok = await update_fact(
                fact_id=fact_id,
                fact=fact_text,
                category=category,
                importance=importance,
                expires_at=expires_at,
                confidence=confidence,
                topics=topics or None,
            )
            return "updated" if ok else "skipped"

    result = await save_fact(
        fact=fact_text,
        category=category,
        source_session_id=str(session_id),
        expires_at=expires_at,
        importance=importance,
        confidence=confidence,
        topics=topics or None,
    )
    return result["status"]
