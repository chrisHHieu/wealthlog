"""CRUD, retrieval, and deduplication for user facts."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.memory.fact_scoring import effective_importance, ensure_aware
from app.config import settings
from app.database import get_session
from app.models.user_fact import UserFact

# Safety bound on the ranking pool — consolidation keeps the live set far
# below this, so in practice every non-expired fact is a candidate.
_FETCH_CAP = 500


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
            # Being injected is not a content change — pin updated_at so the
            # column's onupdate default doesn't reset the staleness clock
            # (effective_importance ages facts by updated_at).
            updated_at=UserFact.updated_at,
        )
    )


async def get_user_facts(
    limit: int = 20,
    track_access: bool = True,
    session_factory=get_session,
) -> list[dict]:
    """Load non-expired user facts for system prompt injection.

    Candidates are fetched broadly and ranked in Python so staleness can be
    priced in (SQL can't see the read-time age penalty). Ranking order, in
    descending priority:
    1. effective importance — stored importance minus age penalty
       (fact_scoring.effective_importance); old facts sink, fresh ones rise.
    2. verified_by_user — user-confirmed beats guessed at equal importance.
    3. confidence — reviewer's certainty hint as the next tie-breaker.
    4. last_accessed_at — frequently-surfaced facts bubble up among equals.
    5. updated_at — freshest wins ties.

    When `track_access` is on, bumps access_count and last_accessed_at for
    the rows returned — disable it for read-only introspection.
    """
    now = datetime.now(UTC)
    epoch = datetime.min.replace(tzinfo=UTC)
    async with session_factory() as db:
        rows = (
            await db.execute(
                select(UserFact)
                .where(
                    or_(
                        UserFact.expires_at.is_(None),
                        UserFact.expires_at > now,
                    ),
                )
                .order_by(UserFact.importance.desc())
                .limit(_FETCH_CAP)
            )
        ).scalars().all()

        eff = {
            r.id: effective_importance(
                r.importance, r.verified_by_user, r.updated_at, now,
            )
            for r in rows
        }

        def _rank(r: UserFact) -> tuple:
            return (
                eff[r.id],
                r.verified_by_user,
                r.confidence,
                ensure_aware(r.last_accessed_at) or epoch,
                ensure_aware(r.updated_at) or epoch,
            )

        selected = sorted(rows, key=_rank, reverse=True)[:limit]

        if track_access:
            await _bump_access(db, [r.id for r in selected])

        return [
            {
                "fact": r.fact,
                "category": r.category,
                "importance": r.importance,
                "effective_importance": eff[r.id],
                "verified_by_user": r.verified_by_user,
                "topics": r.topics or [],
            }
            for r in selected
        ]


def _dedup_candidate_stmt(fact: str, dialect: str, threshold: float):
    """Build the dedup lookup query, dispatching on backend dialect.

    Postgres uses pg_trgm ``similarity()`` so paraphrases collapse onto the
    existing row; the GIN index on ``user_facts.fact`` keeps this O(log n).
    SQLite (used in test fixtures) has no trigram support, so we fall back to
    strict equality — same semantics as the original implementation.
    """
    if dialect == "postgresql":
        score = func.similarity(UserFact.fact, fact)
        return (
            select(UserFact)
            .where(score > threshold)
            .order_by(score.desc())
            .limit(1)
        )
    return select(UserFact).where(UserFact.fact == fact).limit(1)


async def save_user_fact(
    fact: str,
    category: str = "general",
    source_session_id: str | None = None,
    expires_at: datetime | None = None,
    importance: int = 5,
    confidence: int = 5,
    verified_by_user: bool = False,
    topics: list[str] | None = None,
    session_factory=get_session,
) -> dict:
    """Save a new user fact, deduplicating against existing facts.

    Dedup uses trigram similarity on Postgres so paraphrases ("Goal: save 50M
    for car" vs "Saving 50M to buy a car") collapse onto the same row. On
    SQLite we keep the exact-match behavior so the in-memory test fixtures
    continue to work without dialect-specific stubs.
    """
    async with session_factory() as db:
        dialect = db.bind.dialect.name
        stmt = _dedup_candidate_stmt(
            fact, dialect, settings.user_fact_dedup_similarity_threshold,
        )
        existing = await db.execute(stmt)
        if existing.scalar_one_or_none():
            return {"status": "duplicate", "fact": fact}

        new_fact = UserFact(
            fact=fact,
            category=category,
            source_session_id=source_session_id,
            expires_at=expires_at,
            importance=importance,
            confidence=confidence,
            verified_by_user=verified_by_user,
            topics=topics or [],
        )
        db.add(new_fact)
        return {"status": "saved", "fact": fact, "category": category}


async def update_user_fact(
    fact_id: uuid.UUID,
    fact: str,
    category: str,
    importance: int,
    expires_at: datetime | None,
    confidence: int | None = None,
    topics: list[str] | None = None,
    session_factory=get_session,
) -> bool:
    """Replace an existing fact in-place.

    Preserves id, created_at and access stats so the fact's history stays
    continuous — used by the review agent when Haiku judges a new
    observation to be a refinement of an existing fact rather than net-new.

    ``confidence`` is optional so the user-facing edit path can refresh the
    fact text without resetting the reviewer's certainty score; pass an
    explicit value when the reviewer is the caller.
    """
    async with session_factory() as db:
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
        if confidence is not None:
            row.confidence = confidence
        if topics is not None:
            row.topics = topics
        return True


async def delete_user_fact(fact_id: uuid.UUID, session_factory=get_session) -> bool:
    """Delete a user fact by ID."""
    async with session_factory() as db:
        result = await db.execute(
            select(UserFact).where(UserFact.id == fact_id)
        )
        fact = result.scalar_one_or_none()
        if fact:
            await db.delete(fact)
            return True
        return False
