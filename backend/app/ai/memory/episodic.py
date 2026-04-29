"""Episodic memory — summarize past chat sessions and inject them into prompts."""

import json
import re
import unicodedata
import uuid
from datetime import UTC, datetime, timedelta

import anthropic
from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert

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
    topics = payload.get("key_topics") or []
    if not summary_text:
        return False
    if not isinstance(topics, list):
        topics = []
    topics = [str(t).strip() for t in topics if str(t).strip()]
    outcome = (payload.get("outcome") or "").strip() or None

    await _upsert_summary(session_id, summary_text, topics, outcome)
    logger.info(
        "Session %s summarized (%d topics, outcome=%s)",
        session_id, len(topics),
        (outcome[:50] + "…") if outcome and len(outcome) > 50 else outcome,
    )
    return True


async def maybe_summarize_stale_sessions(
    exclude_session_id: uuid.UUID | None = None,
) -> None:
    """Summarize idle sessions whose summary is missing or stale.

    Fire-and-forget: chat router schedules this as a background task. Stale =
    session.updated_at > summary.updated_at (or no summary yet), AND session
    has been idle past the configured window — so we don't summarize live
    conversations.
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

    Recency stays the primary axis: ``limit - topic_hits`` slots go to the
    most-recently-updated rows. Up to ``session_summary_topic_hits`` of the
    remaining slots are filled with older sessions whose ``key_topics``
    intersect the supplied query — this is what recovers "remember when we
    discussed X" without needing embeddings. Pass ``query_topics=None`` (or
    leave it empty) for the original recency-only behavior.
    """
    limit = limit or settings.session_summary_max_recent
    topic_quota = (
        settings.session_summary_topic_hits if query_topics else 0
    )
    recency_quota = max(1, limit - topic_quota)

    async with get_session() as db:
        recent = (await db.execute(
            select(SessionSummary)
            .order_by(SessionSummary.updated_at.desc())
            .limit(recency_quota)
        )).scalars().all()
        recent_ids = {s.id for s in recent}

        topic_hits: list[SessionSummary] = []
        if topic_quota and query_topics:
            topic_hits = await _fetch_topic_overlap_summaries(
                db, query_topics, exclude=recent_ids, limit=topic_quota,
            )

    # Topic hits trail the recent block so the model sees the live context
    # first, then "by the way, here's an older relevant session…"
    return list(recent) + topic_hits


async def build_summaries_prompt(query_topics: list[str] | None = None) -> str:
    """Render session summaries as a system-prompt block.

    ``query_topics`` (typically tokens from the latest user message) drives
    the topic-overlap fan-out; without it, the block is recency-only — same
    behavior as before this knob existed.
    """
    summaries = await get_recent_summaries(query_topics=query_topics)
    if not summaries:
        return ""

    lines = ["[Recent session summaries]"]
    for s in summaries:
        when = _relative_day(s.updated_at)
        lines.append(f"- [{when}] {s.summary}")
        if s.outcome:
            lines.append(f"  Outcome: {s.outcome}")
        if s.key_topics:
            lines.append(f"  Topics: {', '.join(s.key_topics)}")
    lines.append("[End of session summaries]")
    return "\n".join(lines)


# ── Query-topic extraction (cheap, no embeddings) ────────────────────────────


# Drop single-char tokens; keep 2+ so common Vietnamese content words like
# "xe", "đi", "nợ" survive. English stopwords ("of", "am", "is") slip through
# but never appear in Haiku-emitted key_topics, so they're just inert tokens
# in the JSONB ?| query — cheap to ignore.
_MIN_TOKEN_LEN = 2
_TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)


def _extract_query_topics(user_message: str) -> list[str]:
    """Tokenize a user message into the same surface form Haiku stores in key_topics.

    No stemming, no lemmatization, no embedding — just lowercase + Unicode
    word splitting. Vietnamese diacritics are preserved (NFC-normalized)
    because Haiku also emits them verbatim in key_topics, so JSONB ?| stays
    a literal-equality match.
    """
    if not user_message:
        return []
    normalized = unicodedata.normalize("NFC", user_message).lower()
    seen: list[str] = []
    seen_set: set[str] = set()
    for tok in _TOKEN_RE.findall(normalized):
        if len(tok) < _MIN_TOKEN_LEN:
            continue
        if tok in seen_set:
            continue
        seen_set.add(tok)
        seen.append(tok)
    return seen


# ── Internals ────────────────────────────────────────────────────────────────


async def _load_text_messages(session_id: uuid.UUID) -> list[dict]:
    """Load plain text/assistant exchanges, skipping tool_result-only rows."""
    async with get_session() as db:
        rows = (await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at, ChatMessage.id)
        )).scalars().all()
    return [
        {"role": r.role, "content": r.content}
        for r in rows
        if r.content
    ]


async def _call_summarizer(text_msgs: list[dict]) -> dict | None:
    """Call Haiku to produce the summary; return parsed JSON or None on failure."""
    try:
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=settings.session_summary_model,
            max_tokens=512,
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
) -> None:
    """Insert or update the single summary row for this session.

    Postgres path uses ``ON CONFLICT DO UPDATE`` to keep the upsert atomic.
    SQLite (test fixture) doesn't support that dialect-specific clause, so we
    fall back to a manual select-then-write — semantically equivalent at
    single-writer test scale.
    """
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
                )
                .on_conflict_do_update(
                    index_elements=[SessionSummary.session_id],
                    set_={
                        "summary": summary_text,
                        "key_topics": topics,
                        "outcome": outcome,
                        "updated_at": now,
                    },
                )
            )
            await db.execute(stmt)
            return

        existing = (await db.execute(
            select(SessionSummary).where(
                SessionSummary.session_id == session_id,
            )
        )).scalar_one_or_none()
        if existing is None:
            db.add(SessionSummary(
                session_id=session_id,
                summary=summary_text,
                key_topics=topics,
                outcome=outcome,
            ))
        else:
            existing.summary = summary_text
            existing.key_topics = topics
            existing.outcome = outcome
            existing.updated_at = now


async def _fetch_topic_overlap_summaries(
    db,
    query_topics: list[str],
    exclude: set,
    limit: int,
) -> list[SessionSummary]:
    """Pull summaries whose key_topics intersect query_topics, excluding ids.

    Postgres uses the JSONB ``?|`` array-overlap operator (indexable when
    ``key_topics`` has a GIN index). SQLite has no JSON containment ops, so
    we filter in Python after fetching candidates by recency — fine at test
    scale, never hit in production.
    """
    if not query_topics:
        return []

    if db.bind.dialect.name == "postgresql":
        from sqlalchemy import Text, cast, not_
        from sqlalchemy.dialects.postgresql import ARRAY

        # `jsonb ?| text[]` is the supported signature; without the explicit
        # cast asyncpg infers the Python list as jsonb (since the LHS is jsonb)
        # and Postgres rejects it with "operator does not exist: jsonb ?| jsonb".
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

    # SQLite fallback — pull a wider candidate set, intersect in Python.
    rows = (await db.execute(
        select(SessionSummary)
        .order_by(SessionSummary.updated_at.desc())
    )).scalars().all()
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
    """Human-friendly relative date (English).

    SQLite drops timezone info on round-trip while Postgres preserves it, so
    we coerce naive timestamps to UTC before subtracting — without this the
    same code path raises a TypeError on the SQLite test fixture and works
    on Postgres in production.
    """
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
    """Parse a JSON object, tolerating ```json fences Claude sometimes emits."""
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
