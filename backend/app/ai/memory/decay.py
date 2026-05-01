"""Importance decay — gradually reduces importance of stale, low-value facts.

Runs daily as a background loop (started in main.py lifespan).

Rules:
- Only non-verified facts (user-verified facts are ground truth, never touched).
- Only low-importance facts (importance <= DECAY_MAX_IMPORTANCE).
- Only facts not updated in the last DECAY_AGE_DAYS days.
- Floor: importance never goes below DECAY_FLOOR (keeps facts discoverable).
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, update

from app.database import get_session
from app.logging_config import get_logger
from app.models.user_fact import UserFact

logger = get_logger(__name__)

_DECAY_AGE_DAYS = 30
_DECAY_MAX_IMPORTANCE = 5   # only decay facts at or below this level
_DECAY_FLOOR = 1            # never reduce below this


async def decay_old_facts() -> None:
    """Reduce importance by 1 for old unverified low-importance facts."""
    cutoff = datetime.now(UTC) - timedelta(days=_DECAY_AGE_DAYS)
    async with get_session() as db:
        result = await db.execute(
            update(UserFact)
            .where(
                UserFact.verified_by_user == False,   # noqa: E712
                UserFact.importance <= _DECAY_MAX_IMPORTANCE,
                UserFact.importance > _DECAY_FLOOR,
                UserFact.updated_at < cutoff,
            )
            .values(importance=UserFact.importance - 1)
        )
        count = result.rowcount

    if count:
        logger.info("Fact decay: reduced importance on %d stale facts", count)


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
