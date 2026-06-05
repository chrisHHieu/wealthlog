"""Consolidation helpers for user facts."""

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from sqlalchemy import func, or_, select

from app.models.user_fact import UserFact

UpdateFact = Callable[..., Awaitable[bool]]
DeleteFact = Callable[..., Awaitable[bool]]


async def count_active_facts(session_factory) -> int:
    """Count non-expired facts."""
    now = datetime.now(UTC)
    async with session_factory() as db:
        return (
            await db.execute(
                select(func.count(UserFact.id)).where(
                    or_(
                        UserFact.expires_at.is_(None),
                        UserFact.expires_at > now,
                    ),
                )
            )
        ).scalar_one()


async def apply_merge_item(
    item: dict,
    existing: list[tuple[uuid.UUID, str]],
    valid_categories: tuple[str, ...],
    clamp_importance,
    clamp_confidence,
    normalize_topics,
    update_fact: UpdateFact,
    delete_fact: DeleteFact,
) -> tuple[int, int]:
    """Apply one consolidation merge; return (merged_count, removed_count)."""
    if not isinstance(item, dict) or item.get("action") != "merge":
        return 0, 0

    keeps = item.get("keeps")
    removes = item.get("removes") or []
    fact_text = (item.get("fact") or "").strip()
    if not fact_text or not isinstance(keeps, int) or not isinstance(removes, list):
        return 0, 0
    if not (1 <= keeps <= len(existing)):
        return 0, 0

    remove_ids: list[uuid.UUID] = []
    for raw in removes:
        if not isinstance(raw, int) or raw == keeps or not (1 <= raw <= len(existing)):
            continue
        remove_ids.append(existing[raw - 1][0])
    if not remove_ids:
        return 0, 0

    category = item.get("category", "general")
    if category not in valid_categories:
        category = "general"
    importance = clamp_importance(item.get("importance"))
    confidence = clamp_confidence(item.get("confidence"))
    topics = normalize_topics(item.get("topics"), category)

    survivor_id = existing[keeps - 1][0]
    ok = await update_fact(
        fact_id=survivor_id,
        fact=fact_text,
        category=category,
        importance=importance,
        expires_at=None,
        confidence=confidence,
        topics=topics or None,
    )
    if not ok:
        return 0, 0

    removed = 0
    for row_id in remove_ids:
        if await delete_fact(row_id):
            removed += 1
    return 1, removed
