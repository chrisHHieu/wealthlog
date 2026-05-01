"""Long-term memory — user facts CRUD + background extraction agent."""

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta

import anthropic
from sqlalchemy import func, nulls_last, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.model_registry import get_preferred_model, resolve_client_kwargs

from app.ai.memory.prompts import (
    CANONICAL_TOPICS,
    CATEGORY_DEFAULT_TOPICS,
    CONSOLIDATION_PROMPT,
    REVIEW_PROMPT,
)
from app.config import settings
from app.database import get_session
from app.logging_config import get_logger
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

    Ranking order, in descending priority:
    1. importance — reviewer-assigned, drives the broad ordering.
    2. verified_by_user — user-confirmed beats guessed at equal importance.
    3. confidence — reviewer's certainty hint as the next tie-breaker.
    4. last_accessed_at — frequently-surfaced facts bubble up among equals.
    5. updated_at — freshest wins ties.

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
                    UserFact.verified_by_user.desc(),
                    UserFact.confidence.desc(),
                    nulls_last(UserFact.last_accessed_at.desc()),
                    UserFact.updated_at.desc(),
                )
                .limit(limit)
            )
        ).scalars().all()

        if track_access:
            await _bump_access(db, [r.id for r in rows])

        return [
            {
                "fact": r.fact,
                "category": r.category,
                "importance": r.importance,
                "verified_by_user": r.verified_by_user,
                "topics": r.topics or [],
            }
            for r in rows
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
) -> dict:
    """Save a new user fact, deduplicating against existing facts.

    Dedup uses trigram similarity on Postgres so paraphrases ("Goal: save 50M
    for car" vs "Saving 50M to buy a car") collapse onto the same row. On
    SQLite we keep the exact-match behavior so the in-memory test fixtures
    continue to work without dialect-specific stubs.
    """
    async with get_session() as db:
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
) -> bool:
    """Replace an existing fact in-place.

    Preserves id, created_at and access stats so the fact's history stays
    continuous — used by the review agent when Haiku judges a new
    observation to be a refinement of an existing fact rather than net-new.

    ``confidence`` is optional so the user-facing edit path can refresh the
    fact text without resetting the reviewer's certainty score; pass an
    explicit value when the reviewer is the caller.
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
        if confidence is not None:
            row.confidence = confidence
        if topics is not None:
            row.topics = topics
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


_CATEGORY_LABELS = {
    "preference":  "Preference",
    "habit":       "Habit",
    "goal":        "Goal",
    "context":     "Context",
    "pattern":     "Pattern",
    "commitment":  "Commitment",
    "emotion":     "Emotion",
    "general":     "General",
}


def _topic_overlap(fact_topics: list[str], query_topics: list[str]) -> int:
    """Count token-level overlap between stored fact topics and query topic tokens.

    Both sides are lowercased and split on whitespace so multi-word tags like
    'thu nhập' match query tokens ['thu', 'nhập'] extracted from a Vietnamese
    user message.
    """
    if not fact_topics or not query_topics:
        return 0
    fact_tokens: set[str] = set()
    for t in fact_topics:
        fact_tokens.update(t.lower().split())
    query_tokens = {t.lower() for t in query_topics}
    return len(fact_tokens & query_tokens)


async def build_facts_prompt(
    limit: int = 20,
    query_topics: list[str] | None = None,
) -> str:
    """Build a text block of user facts for system prompt injection.

    ``limit`` controls the injection budget. When ``query_topics`` is provided
    (tokens extracted from the latest user message), facts whose stored topics
    overlap with the query are boosted in the ranking — associative retrieval
    without embeddings. The boost is applied in Python after fetching a wider
    pool, so no extra DB round-trip is needed.

    Verified facts get a leading [✓] marker. Topic tags are shown as #tag so
    the agent can reason about what each fact relates to.
    """
    if query_topics:
        # Fetch wider pool, rerank with topic boost, then trim to limit.
        pool = await get_user_facts(limit=min(limit * 3, 120), track_access=False)
        if pool:
            def _score(f: dict) -> int:
                base = f["importance"] * 10 + (5 if f.get("verified_by_user") else 0)
                return base + _topic_overlap(f.get("topics", []), query_topics) * 20
            pool.sort(key=_score, reverse=True)
        facts = pool[:limit]
    else:
        facts = await get_user_facts(limit=limit)

    if not facts:
        return ""

    lines = ["[Known facts about the user]"]
    for f in facts:
        label = _CATEGORY_LABELS.get(f["category"], f["category"])
        marker = "[✓] " if f.get("verified_by_user") else ""
        topics_str = (" " + " ".join(f"#{t}" for t in f["topics"])) if f.get("topics") else ""
        lines.append(f"- {marker}({label}) {f['fact']}{topics_str}")
    lines.append("[End of user facts]")

    return "\n".join(lines)


# ── Background Review Agent ──────────────────────────────────────────────────


_VALID_CATEGORIES = (
    "preference",   # how the user likes things done
    "habit",        # what they regularly do or avoid
    "goal",         # what they are saving or working toward
    "context",      # life situation, role, household
    "pattern",      # behavioral trend observed across multiple sessions
    "commitment",   # something the user explicitly said they will do
    "emotion",      # avoidance signal or emotional pattern
    "general",
)
_DEFAULT_SCORE = 5


def _clamp_score(raw: object) -> int:
    """Coerce a reviewer-emitted 1-10 score into the valid band.

    Shared by the importance and confidence pipelines: both fields have the
    same shape and same failure mode (Haiku occasionally emits floats, strings,
    or None), and one bad value shouldn't poison ordering for the rest.
    """
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        return _DEFAULT_SCORE
    value = int(raw)
    if value < 1:
        return 1
    if value > 10:
        return 10
    return value


# Importance and confidence are semantically distinct (priority vs certainty)
# but share the same 1-10 shape and the same Haiku failure modes — bind both
# names to the one validator so they can never drift apart.
_clamp_importance = _clamp_score
_clamp_confidence = _clamp_score

# Maps common free-form tags Haiku might emit (despite instructions) to canonical.
_TOPIC_ALIASES: dict[str, str] = {
    "lương": "thu nhập", "salary": "thu nhập", "income": "thu nhập", "bonus": "thu nhập",
    "expenses": "chi tiêu", "spending": "chi tiêu", "expense": "chi tiêu", "tiêu": "chi tiêu",
    "budget": "ngân sách",
    "savings": "tiết kiệm", "save": "tiết kiệm",
    "goal": "mục tiêu", "target": "mục tiêu",
    "investment": "đầu tư", "invest": "đầu tư", "stock": "đầu tư", "crypto": "đầu tư",
    "debt": "nợ", "loan": "nợ", "credit": "nợ",
    "account": "tài khoản",
    "plan": "kế hoạch", "planning": "kế hoạch", "strategy": "kế hoạch",
    "subscription": "định kỳ", "recurring": "định kỳ",
    "food": "ăn uống", "dining": "ăn uống",
    "transport": "di chuyển", "vehicle": "di chuyển", "fuel": "di chuyển", "xe": "di chuyển",
    "housing": "nhà ở", "rent": "nhà ở", "nhà": "nhà ở",
    "shopping": "mua sắm", "clothes": "mua sắm",
    "health": "sức khỏe", "insurance": "sức khỏe", "medical": "sức khỏe",
    "entertainment": "giải trí", "leisure": "giải trí", "hobby": "giải trí",
    "education": "giáo dục", "course": "giáo dục", "books": "giáo dục",
    "family": "gia đình", "spouse": "gia đình", "children": "gia đình",
    "work": "công việc", "career": "công việc", "business": "công việc",
    "travel": "du lịch", "vacation": "du lịch",
    "habit": "thói quen", "routine": "thói quen", "pattern": "thói quen",
    "emotion": "cảm xúc", "feeling": "cảm xúc", "avoidance": "cảm xúc",
}

_CANONICAL_SET: frozenset[str] = frozenset(CANONICAL_TOPICS)


def _normalize_topics(raw: object, category: str) -> list[str]:
    """Map raw Haiku-emitted tags to canonical vocabulary.

    1. Accept tags already in the canonical set.
    2. Map known aliases (e.g. 'lương' → 'thu nhập').
    3. Drop anything unrecognized.
    4. Fall back to category default when nothing survives.
    """
    items = raw if isinstance(raw, list) else []
    result: list[str] = []
    seen: set[str] = set()
    for t in items:
        if not isinstance(t, str):
            continue
        normalized = t.lower().strip()
        canonical = normalized if normalized in _CANONICAL_SET else _TOPIC_ALIASES.get(normalized)
        if canonical and canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    if not result:
        result = list(CATEGORY_DEFAULT_TOPICS.get(category, []))
    return result[:3]


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


async def ensure_review_on_session_end(
    session_id: uuid.UUID,
    messages: list[dict],
) -> None:
    """Guarantee at least one fact-extraction pass when a session is closed/summarized.

    Short sessions (< cadence turns) never hit the cadence trigger, so facts
    from them would only be captured via the lossy summary→synthesis path.
    This fires a one-shot review for sessions that haven't had one yet.
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

    # If the cadence review already fired at least once, nothing to do.
    if turn_count == 0 or turn_count >= settings.agent_review_cadence:
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
    confidence = _clamp_confidence(item.get("confidence"))
    expires_at = _compute_expiry(item, category)
    topics = _normalize_topics(item.get("topics"), category)

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
                confidence=confidence,
                topics=topics or None,
            )
            return "updated" if ok else "skipped"
        # Invalid replaces index → fall through to add so the insight isn't lost

    result = await save_user_fact(
        fact=fact_text,
        category=category,
        source_session_id=str(session_id),
        expires_at=expires_at,
        importance=importance,
        confidence=confidence,
        topics=topics or None,
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
            facts_context = f"Known facts:\n{numbered}"
            review_messages.append({
                "role": "user",
                "content": f"{facts_context}\n\n{REVIEW_PROMPT}",
            })
        else:
            review_messages.append({"role": "user", "content": REVIEW_PROMPT})

        active_model = await get_preferred_model()
        client = anthropic.AsyncAnthropic(**resolve_client_kwargs(active_model))
        response = await client.messages.create(
            model=active_model,
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

        await _maybe_consolidate(session_id)

    except json.JSONDecodeError:
        logger.warning("Background review: failed to parse JSON response")
    except Exception:
        logger.exception("Background review failed for session %s", session_id)


# ── Consolidation ───────────────────────────────────────────────────────────


async def _count_active_facts() -> int:
    """Non-expired fact count — drives the consolidation gate."""
    now = datetime.now(UTC)
    async with get_session() as db:
        return (await db.execute(
            select(func.count(UserFact.id)).where(
                or_(
                    UserFact.expires_at.is_(None),
                    UserFact.expires_at > now,
                ),
            )
        )).scalar_one()


async def _maybe_consolidate(session_id: uuid.UUID) -> None:
    """Trigger a Haiku merge pass when the fact count outgrows the budget.

    The threshold check runs *before* any LLM call so the no-op path is free.
    Consolidation reuses :func:`_apply_review_item` but funnels Haiku through
    :data:`CONSOLIDATION_PROMPT`, which only emits 'replace' actions — any
    stray 'add' items are dropped at the routing layer below.
    """
    if not settings.anthropic_api_key:
        return

    threshold = settings.user_fact_consolidation_threshold
    before = await _count_active_facts()
    if before <= threshold:
        return

    logger.info(
        "Consolidation triggered: %d active facts > threshold %d",
        before, threshold,
    )

    existing = await _load_existing_for_review()
    numbered = "\n".join(
        f"{i + 1}. {fact}" for i, (_, fact) in enumerate(existing)
    )

    try:
        active_model = await get_preferred_model()
        client = anthropic.AsyncAnthropic(**resolve_client_kwargs(active_model))
        response = await client.messages.create(
            model=active_model,
            max_tokens=1024,
            temperature=0.3,
            messages=[{
                "role": "user",
                "content": f"Known facts:\n{numbered}\n\n{CONSOLIDATION_PROMPT}",
            }],
        )
        items = json.loads(_strip_code_fence(response.content[0].text))
    except json.JSONDecodeError:
        logger.warning("Consolidation: failed to parse JSON response")
        return
    except Exception:
        logger.exception("Consolidation API call failed")
        return

    if not isinstance(items, list) or not items:
        logger.info("Consolidation: no merges proposed")
        return

    merged = removed = skipped = 0
    for item in items:
        m, r = await _apply_merge_item(item, existing)
        merged += m
        removed += r
        if m == 0 and r == 0:
            skipped += 1

    after = await _count_active_facts()
    logger.info(
        "Consolidation done: %d → %d facts (merged=%d removed=%d skipped=%d)",
        before, after, merged, removed, skipped,
    )


async def _apply_merge_item(
    item: dict,
    existing: list[tuple[uuid.UUID, str]],
) -> tuple[int, int]:
    """Apply one consolidation merge; return (merged_count, removed_count).

    Validates the action, the 'keeps' / 'removes' indices, and the survivor's
    new text before touching the DB. A malformed item collapses to (0, 0)
    so the caller can attribute it to 'skipped' without losing the count.
    """
    if not isinstance(item, dict) or item.get("action") != "merge":
        return 0, 0

    keeps = item.get("keeps")
    removes = item.get("removes") or []
    fact_text = (item.get("fact") or "").strip()
    if not fact_text or not isinstance(keeps, int) or not isinstance(removes, list):
        return 0, 0
    if not (1 <= keeps <= len(existing)):
        return 0, 0

    # Survivor must not also appear in the remove list — otherwise we'd delete
    # the row we just updated. Skip rather than guess at intent.
    remove_ids: list[uuid.UUID] = []
    for raw in removes:
        if not isinstance(raw, int) or raw == keeps or not (1 <= raw <= len(existing)):
            continue
        remove_ids.append(existing[raw - 1][0])
    if not remove_ids:
        return 0, 0

    category = item.get("category", "general")
    if category not in _VALID_CATEGORIES:
        category = "general"
    importance = _clamp_importance(item.get("importance"))
    confidence = _clamp_confidence(item.get("confidence"))
    topics = _normalize_topics(item.get("topics"), category)

    survivor_id = existing[keeps - 1][0]
    ok = await update_user_fact(
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
    for rid in remove_ids:
        if await delete_user_fact(rid):
            removed += 1
    return 1, removed
