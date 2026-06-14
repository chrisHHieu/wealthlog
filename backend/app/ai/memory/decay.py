"""Staleness sunset + expiry purge for user facts.

Importance is never mutated by time — ranking prices staleness in at read
time via ``fact_scoring.effective_importance`` (lazy decay). The daily loop
(started in main.py lifespan) only handles the destructive tail end:

- ``sunset_stale_facts`` stamps a 30-day expiry on facts that have sat at the
  effective-importance floor long enough. During that window a reviewer
  refresh rewrites the expiry (update_user_fact), so a revived fact escapes;
  otherwise it flows into the existing dreaming → purge pipeline.
- ``purge_expired_facts`` permanently deletes facts whose expiry has passed.

Sunset rules:
- Only non-verified facts (user-verified facts are ground truth, never touched).
- Only facts already at the effective floor — high-importance facts take
  proportionally longer to sink there (one point per 30 stale days).
- Never sooner than ``_SUNSET_MIN_STALE_DAYS`` without a content update, so
  facts born at importance 1-2 aren't stamped while still fresh.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.ai.memory.fact_scoring import (
    EFFECTIVE_IMPORTANCE_FLOOR,
    effective_importance,
    ensure_aware,
)
from app.database import get_session
from app.logging_config import get_logger
from app.models.user_fact import UserFact

logger = get_logger(__name__)

_SUNSET_MIN_STALE_DAYS = 90
_SUNSET_GRACE_DAYS = 30


async def sunset_stale_facts() -> None:
    """Stamp a grace-period expiry on unverified facts stuck at the floor."""
    now = datetime.now(UTC)
    stale_cutoff = now - timedelta(days=_SUNSET_MIN_STALE_DAYS)
    async with get_session() as db:
        rows = (
            await db.execute(
                select(UserFact).where(
                    UserFact.verified_by_user == False,  # noqa: E712
                    UserFact.expires_at.is_(None),
                )
            )
        ).scalars().all()

        count = 0
        for row in rows:
            updated = ensure_aware(row.updated_at)
            if updated is None or updated >= stale_cutoff:
                continue
            eff = effective_importance(row.importance, False, row.updated_at, now)
            if eff > EFFECTIVE_IMPORTANCE_FLOOR:
                continue
            row.expires_at = now + timedelta(days=_SUNSET_GRACE_DAYS)
            count += 1

    if count:
        logger.info("Fact sunset: stamped expiry on %d stale facts", count)


async def purge_expired_facts() -> None:
    """Permanently delete facts whose expires_at has passed."""
    now = datetime.now(UTC)
    async with get_session() as db:
        result = await db.execute(
            delete(UserFact).where(
                UserFact.expires_at.is_not(None),
                UserFact.expires_at < now,
            )
        )
        count = result.rowcount

    if count:
        logger.info("Fact purge: deleted %d expired facts", count)
