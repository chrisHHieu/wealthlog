"""Long-term memory — user facts CRUD + background extraction agent."""

import asyncio
import uuid
from datetime import datetime

import anthropic
from sqlalchemy import func, select

from app.ai.memory.fact_consolidation import apply_merge_item as _consolidation_apply_merge
from app.ai.memory.fact_consolidation import count_active_facts
from app.ai.memory.fact_consolidation_runner import maybe_consolidate
from app.ai.memory.fact_prompting import format_facts_prompt, rerank_facts_for_prompt
from app.ai.memory.fact_prompting import topic_overlap as _prompt_topic_overlap
from app.ai.memory.fact_review import apply_review_item as _review_apply_item
from app.ai.memory.fact_review import load_existing_for_review
from app.ai.memory.fact_review_runner import run_review
from app.ai.memory.fact_scoring import (
    _clamp_confidence,
    _clamp_importance,
    _normalize_topics,
)
from app.ai.memory.fact_scoring import _clamp_score as _fact_clamp_score
from app.ai.memory.fact_scoring import _compute_expiry as _scoring_compute_expiry
from app.ai.memory.fact_store import _bump_access as _fact_bump_access
from app.ai.memory.fact_store import _dedup_candidate_stmt as _fact_dedup_candidate_stmt
from app.ai.memory.fact_store import delete_user_fact as _store_delete_user_fact
from app.ai.memory.fact_store import get_user_facts as _store_get_user_facts
from app.ai.memory.fact_store import save_user_fact as _store_save_user_fact
from app.ai.memory.fact_store import update_user_fact as _store_update_user_fact
from app.ai.memory.prompts import (
    CONSOLIDATION_PROMPT,
    REVIEW_PROMPT,
)
from app.ai.memory.review_parsing import (
    extract_text as _extract_text,
)
from app.ai.memory.review_parsing import (
    has_api_key as _has_api_key,
)
from app.ai.memory.review_parsing import (
    strip_code_fence as _strip_code_fence,
)
from app.ai.model_registry import get_structured_model, resolve_client_kwargs
from app.config import settings
from app.database import get_session
from app.logging_config import get_logger
from app.models.chat import ChatMessage

logger = get_logger(__name__)
_bump_access = _fact_bump_access
_clamp_score = _fact_clamp_score
_dedup_candidate_stmt = _fact_dedup_candidate_stmt
_topic_overlap = _prompt_topic_overlap


# ── User Facts CRUD ──────────────────────────────────────────────────────────


def _compute_expiry(item: dict, category: str) -> datetime | None:
    return _scoring_compute_expiry(
        item,
        category,
        context_ttl_days=settings.user_fact_default_context_ttl_days,
    )


async def get_user_facts(limit: int = 20, track_access: bool = True) -> list[dict]:
    return await _store_get_user_facts(
        limit=limit,
        track_access=track_access,
        session_factory=get_session,
    )


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
    return await _store_save_user_fact(
        fact=fact,
        category=category,
        source_session_id=source_session_id,
        expires_at=expires_at,
        importance=importance,
        confidence=confidence,
        verified_by_user=verified_by_user,
        topics=topics,
        session_factory=get_session,
    )


async def update_user_fact(
    fact_id: uuid.UUID,
    fact: str,
    category: str,
    importance: int,
    expires_at: datetime | None,
    confidence: int | None = None,
    topics: list[str] | None = None,
) -> bool:
    return await _store_update_user_fact(
        fact_id=fact_id,
        fact=fact,
        category=category,
        importance=importance,
        expires_at=expires_at,
        confidence=confidence,
        topics=topics,
        session_factory=get_session,
    )


async def delete_user_fact(fact_id: uuid.UUID) -> bool:
    return await _store_delete_user_fact(
        fact_id=fact_id,
        session_factory=get_session,
    )


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
        facts = rerank_facts_for_prompt(pool, query_topics)[:limit]
    else:
        facts = await get_user_facts(limit=limit)

    return format_facts_prompt(facts)


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
    return await load_existing_for_review(get_session)


async def _apply_review_item(
    item: dict,
    existing: list[tuple[uuid.UUID, str]],
    session_id: uuid.UUID,
) -> str:
    """Route one reviewer item to add/update and return the outcome tag.

    Outcomes: 'saved', 'updated', 'duplicate', 'skipped'. Kept as strings
    so the caller can log counts without caring about internal details.
    """
    return await _review_apply_item(
        item=item,
        existing=existing,
        session_id=session_id,
        valid_categories=_VALID_CATEGORIES,
        clamp_importance=_clamp_importance,
        clamp_confidence=_clamp_confidence,
        compute_expiry=_compute_expiry,
        normalize_topics=_normalize_topics,
        save_fact=save_user_fact,
        update_fact=update_user_fact,
    )


async def _run_review(
    session_id: uuid.UUID,
    messages: list[dict],
) -> None:
    """Background task: use Claude to extract or refine user facts.

    Sends conversation + numbered list of existing facts to Haiku, which
    returns add/replace actions. Routing and dedup live in
    :func:`_apply_review_item`.
    """
    await run_review(
        session_id=session_id,
        messages=messages,
        settings_obj=settings,
        logger=logger,
        anthropic_client_factory=anthropic.AsyncAnthropic,
        resolve_client_kwargs=resolve_client_kwargs,
        get_structured_model=get_structured_model,
        has_api_key=_has_api_key,
        extract_text=_extract_text,
        strip_code_fence=_strip_code_fence,
        load_existing=_load_existing_for_review,
        apply_review_item=_apply_review_item,
        maybe_consolidate=_maybe_consolidate,
        review_prompt=REVIEW_PROMPT,
    )


# ── Consolidation ───────────────────────────────────────────────────────────


async def _count_active_facts() -> int:
    """Non-expired fact count — drives the consolidation gate."""
    return await count_active_facts(get_session)


async def _maybe_consolidate(_session_id: uuid.UUID) -> None:
    """Trigger a Haiku merge pass when the fact count outgrows the budget.

    The threshold check runs *before* any LLM call so the no-op path is free.
    Consolidation reuses :func:`_apply_review_item` but funnels Haiku through
    :data:`CONSOLIDATION_PROMPT`, which only emits 'replace' actions — any
    stray 'add' items are dropped at the routing layer below.
    """
    await maybe_consolidate(
        _session_id=_session_id,
        settings_obj=settings,
        logger=logger,
        anthropic_client_factory=anthropic.AsyncAnthropic,
        resolve_client_kwargs=resolve_client_kwargs,
        get_structured_model=get_structured_model,
        has_api_key=_has_api_key,
        extract_text=_extract_text,
        strip_code_fence=_strip_code_fence,
        count_active_facts=_count_active_facts,
        load_existing=_load_existing_for_review,
        apply_merge_item=_apply_merge_item,
        consolidation_prompt=CONSOLIDATION_PROMPT,
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
    return await _consolidation_apply_merge(
        item=item,
        existing=existing,
        valid_categories=_VALID_CATEGORIES,
        clamp_importance=_clamp_importance,
        clamp_confidence=_clamp_confidence,
        normalize_topics=_normalize_topics,
        update_fact=update_user_fact,
        delete_fact=delete_user_fact,
    )
