"""UserModel synthesis — periodic Sonnet pass that writes a coherent user profile."""

import asyncio
from datetime import UTC, datetime

import anthropic
from sqlalchemy import delete, func, select

from app.ai.memory.episodic import get_recent_summaries
from app.ai.memory.facts import get_user_facts
from app.ai.memory.prompts import SYNTHESIS_PROMPT
from app.ai.model_registry import get_structured_model, resolve_client_kwargs
from app.config import settings
from app.database import get_session
from app.logging_config import get_logger
from app.models.session_summary import SessionSummary
from app.models.user_fact import UserFact
from app.models.user_model import UserModel

logger = get_logger(__name__)


# ── Public API ───────────────────────────────────────────────────────────────


async def get_latest_user_model() -> UserModel | None:
    """Return the latest UserModel row, or None if not yet created."""
    try:
        async with get_session() as db:
            return (
                await db.execute(
                    select(UserModel)
                    .order_by(UserModel.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
    except Exception:
        logger.debug("Could not load latest UserModel", exc_info=True)
        return None


async def get_user_model_text() -> str | None:
    """Return the latest synthesized user model content, or None if not yet created."""
    row = await get_latest_user_model()
    return row.content if row else None


async def force_synthesize_user_model() -> None:
    """Immediately run synthesis regardless of cadence — used after onboarding."""
    if not settings.anthropic_api_key and not settings.deepseek_api_key:
        return
    async with get_session() as db:
        session_count = (
            await db.execute(select(func.count(SessionSummary.id)))
        ).scalar_one()
    await _run_synthesis(session_count)


async def _count_new_facts_since(since: datetime | None) -> int:
    """Count facts created after ``since``. Pass None to count all facts."""
    async with get_session() as db:
        stmt = select(func.count(UserFact.id))
        if since is not None:
            stmt = stmt.where(UserFact.created_at > since)
        return (await db.execute(stmt)).scalar_one()


async def maybe_synthesize_user_model() -> None:
    """Schedule a background synthesis if enough new sessions OR new facts have accumulated,
    or if the existing model is too stale.

    Three triggers (whichever fires first):
    1. Session cadence — delta >= ``user_model_synthesis_cadence`` new summarized sessions.
    2. Fact delta     — >= ``user_model_fact_delta_threshold`` new facts since last synthesis.
    3. Staleness      — model older than ``user_model_max_age_days`` AND at least 1 new fact exists.

    The check is cheap (three COUNT queries) so it can run on every turn.
    """
    if not settings.anthropic_api_key and not settings.deepseek_api_key:
        return

    async with get_session() as db:
        total_sessions = (
            await db.execute(select(func.count(SessionSummary.id)))
        ).scalar_one()

        latest = (
            await db.execute(
                select(UserModel)
                .order_by(UserModel.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    last_count = latest.session_count if latest else 0
    session_trigger = (total_sessions - last_count) >= settings.user_model_synthesis_cadence

    new_facts = 0
    fact_trigger = False
    staleness_trigger = False

    if not session_trigger:
        since = latest.created_at if latest else None
        new_facts = await _count_new_facts_since(since)
        fact_trigger = new_facts >= settings.user_model_fact_delta_threshold

    if not session_trigger and not fact_trigger and latest is not None:
        age_days = (datetime.now(UTC) - latest.created_at).days
        if age_days >= settings.user_model_max_age_days:
            # Re-synthesize if stale even with minimal new data
            since = latest.created_at
            if new_facts == 0:
                new_facts = await _count_new_facts_since(since)
            staleness_trigger = new_facts >= 1

    if not session_trigger and not fact_trigger and not staleness_trigger:
        return

    if session_trigger:
        reason = "session cadence"
    elif fact_trigger:
        reason = f"fact delta ({new_facts} new facts)"
    else:
        age_days = (datetime.now(UTC) - latest.created_at).days
        reason = f"staleness ({age_days}d old, {new_facts} new facts)"

    logger.info("Scheduling UserModel synthesis — trigger: %s", reason)
    asyncio.create_task(_run_synthesis(total_sessions))


# ── Background synthesis ─────────────────────────────────────────────────────


async def _run_synthesis(session_count: int) -> None:
    """Build a fresh UserModel from all facts + recent session summaries."""
    try:
        logger.info("UserModel synthesis started (session_count=%d)", session_count)

        facts = await get_user_facts(limit=50, track_access=False)
        summaries = await get_recent_summaries(limit=20)
        existing = await get_user_model_text()

        prompt = _build_synthesis_input(facts, summaries, existing)

        active_model = await get_structured_model()
        client = anthropic.AsyncAnthropic(**resolve_client_kwargs(active_model))
        response = await client.messages.create(
            model=active_model,
            max_tokens=8000,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )

        content = next(
            (b.text for b in response.content if b.type == "text"), ""
        ).strip()
        if not content:
            logger.warning("UserModel synthesis returned empty content")
            return

        await _save_user_model(content, session_count)
        logger.info("UserModel synthesis complete (session_count=%d)", session_count)

    except Exception:
        logger.exception("UserModel synthesis failed")


def _build_synthesis_input(
    facts: list[dict],
    summaries: list,
    existing: str | None,
) -> str:
    parts: list[str] = []

    if facts:
        lines = ["[Known facts about the user]"]
        for f in facts:
            marker = "[✓] " if f.get("verified_by_user") else ""
            topics_str = (" " + " ".join(f"#{t}" for t in f["topics"])) if f.get("topics") else ""
            lines.append(f"- {marker}({f['category']}) {f['fact']}{topics_str}")
        parts.append("\n".join(lines))

    if summaries:
        lines = ["[Recent session summaries]"]
        for s in summaries:
            lines.append(f"- {s.summary}")
            if s.outcome:
                lines.append(f"  Outcome: {s.outcome}")
            if s.commitments:
                lines.append(f"  Commitments: {', '.join(s.commitments)}")
            if s.pushback:
                lines.append(f"  Pushback: {s.pushback}")
        parts.append("\n".join(lines))

    if existing:
        parts.append(
            f"[Current user model — update if new information warrants it]\n{existing}"
        )

    parts.append(SYNTHESIS_PROMPT)
    return "\n\n".join(parts)


async def _save_user_model(content: str, session_count: int) -> None:
    """Persist a new UserModel version and prune old ones."""
    async with get_session() as db:
        max_version = (
            await db.execute(select(func.max(UserModel.version)))
        ).scalar_one() or 0

        db.add(UserModel(
            content=content,
            session_count=session_count,
            version=max_version + 1,
            created_at=datetime.now(UTC),
        ))

    await _prune_old_versions()


async def _prune_old_versions() -> None:
    """Keep only the latest N versions; delete older rows."""
    keep = settings.user_model_max_versions
    async with get_session() as db:
        keep_ids = (
            await db.execute(
                select(UserModel.id)
                .order_by(UserModel.created_at.desc())
                .limit(keep)
            )
        ).scalars().all()

        if keep_ids:
            await db.execute(
                delete(UserModel).where(UserModel.id.not_in(keep_ids))
            )
