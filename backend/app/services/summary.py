"""Episodic memory — summarize past chat sessions and inject them into prompts."""

import json
import uuid
from datetime import UTC, datetime, timedelta

import anthropic
from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.logging_config import get_logger
from app.mcp.db import get_session
from app.models.chat import ChatMessage, ChatSession
from app.models.session_summary import SessionSummary

logger = get_logger(__name__)


_SUMMARY_PROMPT = (
    "Summarize the personal-finance conversation above.\n\n"
    "Requirements:\n"
    "- summary: 2-4 sentences. State what the user asked, what was done, what "
    "was concluded. No greetings, no meta-comments, no honorifics. Write in "
    "the SAME LANGUAGE as the conversation above.\n"
    "- key_topics: 2-5 main topics, each 1-3 words (e.g., \"budget\", "
    "\"car savings\", \"food spending\" / \"ngân sách\", \"tiết kiệm mua xe\"). "
    "Match the conversation's language.\n"
    "- If the session is only greetings / no substance, use "
    "summary='No substantive content.' and key_topics=[].\n\n"
    "Return ONLY a JSON object (no markdown, no explanation):\n"
    '{"summary": "...", "key_topics": ["...", "..."]}'
)


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

    await _upsert_summary(session_id, summary_text, topics)
    logger.info(
        "Session %s summarized (%d topics)", session_id, len(topics),
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


async def get_recent_summaries(limit: int | None = None) -> list[SessionSummary]:
    """Fetch N most recently-updated session summaries."""
    limit = limit or settings.session_summary_max_recent
    async with get_session() as db:
        rows = (await db.execute(
            select(SessionSummary)
            .order_by(SessionSummary.updated_at.desc())
            .limit(limit)
        )).scalars().all()
    return list(rows)


async def build_summaries_prompt() -> str:
    """Render recent session summaries as a system-prompt block."""
    summaries = await get_recent_summaries()
    if not summaries:
        return ""

    lines = ["[Recent session summaries]"]
    for s in summaries:
        when = _relative_day(s.updated_at)
        lines.append(f"- [{when}] {s.summary}")
        if s.key_topics:
            lines.append(f"  Topics: {', '.join(s.key_topics)}")
    lines.append("[End of session summaries]")
    return "\n".join(lines)


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
                {"role": "user", "content": _SUMMARY_PROMPT},
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
) -> None:
    """Insert or update the single summary row for this session."""
    now = datetime.now(UTC)
    stmt = (
        insert(SessionSummary)
        .values(
            session_id=session_id,
            summary=summary_text,
            key_topics=topics,
        )
        .on_conflict_do_update(
            index_elements=[SessionSummary.session_id],
            set_={
                "summary": summary_text,
                "key_topics": topics,
                "updated_at": now,
            },
        )
    )
    async with get_session() as db:
        await db.execute(stmt)


def _relative_day(dt: datetime) -> str:
    """Human-friendly relative date (English)."""
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
