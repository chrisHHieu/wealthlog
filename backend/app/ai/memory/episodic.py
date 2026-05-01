"""Episodic memory — summarize past chat sessions and inject them into prompts."""

import json
import re
import unicodedata
import uuid
from datetime import UTC, datetime, timedelta

import anthropic
from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert

from app.ai.model_registry import get_preferred_model, resolve_client_kwargs

from app.ai.memory.facts import ensure_review_on_session_end
from app.ai.memory.prompts import SUMMARY_PROMPT
from app.config import settings
from app.database import get_session
from app.logging_config import get_logger
from app.models.chat import ChatMessage, ChatSession
from app.models.session_summary import SessionSummary

logger = get_logger(__name__)


# ── Summarization ────────────────────────────────────────────────────────────


async def summarize_session(session_id: uuid.UUID) -> bool:
    """Produce (or refresh) an episodic summary for one session.

    Returns True if a row was written, False if skipped (no content, API key
    missing, malformed response, or session ended mid-turn).
    """
    if not settings.anthropic_api_key:
        return False

    text_msgs = await _load_text_messages(session_id)
    if len(text_msgs) < 2 or text_msgs[-1]["role"] != "assistant":
        return False

    payload = await _call_summarizer(text_msgs)
    if not payload:
        return False

    summary_text = (payload.get("summary") or "").strip()
    if not summary_text:
        return False

    topics = payload.get("key_topics") or []
    if not isinstance(topics, list):
        topics = []
    topics = [str(t).strip() for t in topics if str(t).strip()]

    outcome = (payload.get("outcome") or "").strip() or None

    commitments = payload.get("commitments") or []
    if not isinstance(commitments, list):
        commitments = []
    commitments = [str(c).strip() for c in commitments if str(c).strip()]

    pushback = (payload.get("pushback") or "").strip() or None

    open_questions = payload.get("open_questions") or []
    if not isinstance(open_questions, list):
        open_questions = []
    open_questions = [str(q).strip() for q in open_questions if str(q).strip()]

    await _upsert_summary(
        session_id, summary_text, topics, outcome,
        commitments, pushback, open_questions,
    )

    if commitments:
        await _save_commitments(session_id, commitments)

    logger.info(
        "Session %s summarized (%d topics, %d commitments, outcome=%s)",
        session_id, len(topics), len(commitments),
        (outcome[:50] + "…") if outcome and len(outcome) > 50 else outcome,
    )

    # Ensure short sessions (< cadence turns) still get fact extraction.
    await ensure_review_on_session_end(session_id, text_msgs)

    return True


async def maybe_summarize_stale_sessions(
    exclude_session_id: uuid.UUID | None = None,
) -> None:
    """Summarize idle sessions whose summary is missing or stale.

    Fire-and-forget: chat router schedules this as a background task.
    """
    idle_cutoff = datetime.now(UTC) - timedelta(
        minutes=settings.session_summary_idle_minutes,
    )

    async with get_session() as db:
        q = (
            select(ChatSession.id)
            .outerjoin(
                SessionSummary,
                SessionSummary.session_id == ChatSession.id,
            )
            .where(ChatSession.updated_at < idle_cutoff)
            .where(
                or_(
                    SessionSummary.id.is_(None),
                    SessionSummary.updated_at < ChatSession.updated_at,
                ),
            )
            .order_by(ChatSession.updated_at.desc())
            .limit(20)
        )
        if exclude_session_id is not None:
            q = q.where(ChatSession.id != exclude_session_id)

        stale_ids = [row[0] for row in (await db.execute(q)).all()]

    if not stale_ids:
        return

    logger.info("Summarizing %d stale session(s)", len(stale_ids))
    for sid in stale_ids:
        try:
            await summarize_session(sid)
        except Exception:
            logger.exception("Summarization failed for session %s", sid)


# ── Retrieval / prompt injection ─────────────────────────────────────────────


async def get_recent_summaries(
    query_topics: list[str] | None = None,
    limit: int | None = None,
) -> list[SessionSummary]:
    """Fetch session summaries blending recency with topic-overlap.

    ``limit`` is driven by the caller so the prompt builder can reduce it
    when a UserModel is present (the model already covers the broader history).
    """
    limit = limit or settings.session_summary_max_recent
    topic_quota = settings.session_summary_topic_hits if query_topics else 0
    recency_quota = max(1, limit - topic_quota)

    async with get_session() as db:
        recent = (
            await db.execute(
                select(SessionSummary)
                .order_by(SessionSummary.updated_at.desc())
                .limit(recency_quota)
            )
        ).scalars().all()
        recent_ids = {s.id for s in recent}

        topic_hits: list[SessionSummary] = []
        if topic_quota and query_topics:
            topic_hits = await _fetch_topic_overlap_summaries(
                db, query_topics, exclude=recent_ids, limit=topic_quota,
            )

    return list(recent) + topic_hits


async def build_summaries_prompt(
    query_topics: list[str] | None = None,
    limit: int | None = None,
) -> str:
    """Render session summaries as a system-prompt block.

    Includes pushback and open_questions when present — these give the agent
    awareness of sensitive topics and open conversation threads.
    """
    summaries = await get_recent_summaries(query_topics=query_topics, limit=limit)
    if not summaries:
        return ""

    lines = ["[Recent session summaries]"]
    for s in summaries:
        when = _relative_day(s.updated_at)
        lines.append(f"- [{when}] {s.summary}")
        if s.outcome:
            lines.append(f"  Outcome: {s.outcome}")
        if s.pushback:
            lines.append(f"  Pushback: {s.pushback}")
        if s.open_questions:
            lines.append(f"  Open: {'; '.join(s.open_questions)}")
        if s.key_topics:
            lines.append(f"  Topics: {', '.join(s.key_topics)}")
    lines.append("[End of session summaries]")
    return "\n".join(lines)


# ── Query-topic extraction (cheap, no embeddings) ────────────────────────────


_MIN_TOKEN_LEN = 2
_TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)


def _extract_query_topics(user_message: str) -> list[str]:
    """Tokenize a user message into surface-form tokens for topic-overlap matching."""
    if not user_message:
        return []
    normalized = unicodedata.normalize("NFC", user_message).lower()
    seen: list[str] = []
    seen_set: set[str] = set()
    for tok in _TOKEN_RE.findall(normalized):
        if len(tok) < _MIN_TOKEN_LEN or tok in seen_set:
            continue
        seen_set.add(tok)
        seen.append(tok)
    return seen


# ── Internals ────────────────────────────────────────────────────────────────


async def _load_text_messages(session_id: uuid.UUID) -> list[dict]:
    async with get_session() as db:
        rows = (
            await db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at, ChatMessage.id)
            )
        ).scalars().all()
    return [{"role": r.role, "content": r.content} for r in rows if r.content]


async def _call_summarizer(text_msgs: list[dict]) -> dict | None:
    try:
        active_model = await get_preferred_model()
        client = anthropic.AsyncAnthropic(**resolve_client_kwargs(active_model))
        response = await client.messages.create(
            model=active_model,
            max_tokens=700,
            temperature=0.3,
            messages=[
                *text_msgs,
                {"role": "user", "content": SUMMARY_PROMPT},
            ],
        )
        return _extract_json(response.content[0].text)
    except Exception:
        logger.exception("Summary API call failed")
        return None


async def _upsert_summary(
    session_id: uuid.UUID,
    summary_text: str,
    topics: list[str],
    outcome: str | None,
    commitments: list[str],
    pushback: str | None,
    open_questions: list[str],
) -> None:
    now = datetime.now(UTC)
    async with get_session() as db:
        if db.bind.dialect.name == "postgresql":
            stmt = (
                insert(SessionSummary)
                .values(
                    session_id=session_id,
                    summary=summary_text,
                    key_topics=topics,
                    outcome=outcome,
                    commitments=commitments or None,
                    pushback=pushback,
                    open_questions=open_questions or None,
                )
                .on_conflict_do_update(
                    index_elements=[SessionSummary.session_id],
                    set_={
                        "summary": summary_text,
                        "key_topics": topics,
                        "outcome": outcome,
                        "commitments": commitments or None,
                        "pushback": pushback,
                        "open_questions": open_questions or None,
                        "updated_at": now,
                    },
                )
            )
            await db.execute(stmt)
            return

        # SQLite fallback for tests
        existing = (
            await db.execute(
                select(SessionSummary).where(SessionSummary.session_id == session_id)
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(SessionSummary(
                session_id=session_id,
                summary=summary_text,
                key_topics=topics,
                outcome=outcome,
                commitments=commitments or None,
                pushback=pushback,
                open_questions=open_questions or None,
            ))
        else:
            existing.summary = summary_text
            existing.key_topics = topics
            existing.outcome = outcome
            existing.commitments = commitments or None
            existing.pushback = pushback
            existing.open_questions = open_questions or None
            existing.updated_at = now


async def _save_commitments(
    session_id: uuid.UUID,
    commitments: list[str],
) -> None:
    """Persist each commitment string as a UserCommitment row."""
    from app.ai.memory.commitments import save_commitment
    for text in commitments:
        try:
            await save_commitment(text=text, source_session_id=session_id)
        except Exception:
            logger.exception("Failed to save commitment: %s", text)


async def _fetch_topic_overlap_summaries(
    db,
    query_topics: list[str],
    exclude: set,
    limit: int,
) -> list[SessionSummary]:
    if not query_topics:
        return []

    if db.bind.dialect.name == "postgresql":
        from sqlalchemy import Text, cast, not_
        from sqlalchemy.dialects.postgresql import ARRAY

        stmt = (
            select(SessionSummary)
            .where(
                SessionSummary.key_topics.op("?|")(
                    cast(query_topics, ARRAY(Text)),
                ),
            )
            .order_by(SessionSummary.updated_at.desc())
            .limit(limit + len(exclude))
        )
        if exclude:
            stmt = stmt.where(not_(SessionSummary.id.in_(exclude)))
        rows = (await db.execute(stmt)).scalars().all()
        return list(rows)[:limit]

    # SQLite fallback
    rows = (
        await db.execute(
            select(SessionSummary).order_by(SessionSummary.updated_at.desc())
        )
    ).scalars().all()
    wanted = set(query_topics)
    matches: list[SessionSummary] = []
    for row in rows:
        if row.id in exclude:
            continue
        if wanted.intersection(row.key_topics or []):
            matches.append(row)
            if len(matches) >= limit:
                break
    return matches


def _relative_day(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    days = (now - dt).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 7:
        return f"{days} days ago"
    if days < 30:
        return f"{days // 7} week(s) ago"
    return dt.strftime("%d/%m")


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Summary: failed to parse JSON response")
        return None
    return data if isinstance(data, dict) else None
