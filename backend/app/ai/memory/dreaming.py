"""Dreaming pass — nightly rewrite of expired time-bound memories.

Runs daily right before ``purge_expired_facts()`` (see the maintenance loop
in ``main.py``). Expired facts would otherwise vanish silently; instead this
pass reviews them against the user's real financial data and rewrites the
ones worth keeping as past-tense outcome facts — "Saving 50M for a car by
Jun 2026" becomes "Saved 42M of the 50M car goal by Jun 2026". Facts the
model drops (or fails to mention) are left for the purge to delete, so the
worst case degrades to the old behavior. The same evidence resolves overdue
commitments to done/abandoned.

A rewrite clears ``expires_at`` (the outcome is evergreen history) and keeps
``verified_by_user`` — provenance of the original statement still holds; the
outcome's certainty lives in ``confidence``.
"""

import json
from datetime import UTC, datetime, timedelta, timezone

import anthropic
from sqlalchemy import or_, select, update

from app.ai.agent.tools import execute_tool
from app.ai.memory.fact_scoring import (
    _clamp_confidence,
    _clamp_importance,
    _normalize_topics,
)
from app.ai.memory.fact_store import update_user_fact
from app.ai.memory.prompts import DREAMING_PROMPT
from app.ai.memory.review_parsing import extract_text, has_api_key, strip_code_fence
from app.ai.model_registry import get_structured_model, resolve_client_kwargs
from app.config import settings
from app.database import get_session
from app.logging_config import get_logger
from app.models.user_commitment import UserCommitment
from app.models.user_fact import UserFact

logger = get_logger(__name__)

_VN_TZ = timezone(timedelta(hours=7))

# Prompt-size caps. Overflow facts are simply purged unrewritten — same as
# the pre-dreaming behavior — and a single-user app rarely expires more than
# a handful of facts per day anyway.
_MAX_FACTS = 20
_MAX_COMMITMENTS = 10
# Pending commitments older than this stop surfacing in the agent prompt
# (see commitments.get_pending_commitments), so dreaming is their last
# chance to be resolved instead of lingering pending forever.
_COMMITMENT_STALE_DAYS = 30

_RESOLVE_STATUSES = ("done", "abandoned")
_EVIDENCE_TOOLS: tuple[tuple[str, dict], ...] = (
    ("get_financial_summary", {}),  # month filled in at call time
    ("get_goals", {}),
)


# ── Public API ───────────────────────────────────────────────────────────────


async def run_dreaming_pass(session_factory=get_session) -> None:
    """Rewrite expired facts and resolve overdue commitments, once a day."""
    if not has_api_key(getattr(settings, "anthropic_api_key", "")) and not has_api_key(
        getattr(settings, "deepseek_api_key", ""),
    ):
        return

    facts = await _load_expired_facts(session_factory)
    commitments = await _load_overdue_commitments(session_factory)
    if not facts and not commitments:
        return

    logger.info(
        "Dreaming pass started — %d expired facts, %d overdue commitments",
        len(facts), len(commitments),
    )

    evidence = await _gather_financial_evidence()
    items = await _call_dreamer(_build_prompt(evidence, facts, commitments))
    if items is None:
        return

    counts = {"rewritten": 0, "dropped": 0, "resolved": 0, "skipped": 0}
    for item in items:
        outcome = await _apply_dream_item(item, facts, commitments, session_factory)
        counts[outcome] = counts.get(outcome, 0) + 1

    logger.info(
        "Dreaming pass done — rewritten=%d dropped=%d resolved=%d skipped=%d",
        counts["rewritten"], counts["dropped"], counts["resolved"], counts["skipped"],
    )


# ── Candidate loading ────────────────────────────────────────────────────────


async def _load_expired_facts(session_factory) -> list[UserFact]:
    """Facts whose expiry has passed — tonight's purge would delete these."""
    now = datetime.now(UTC)
    async with session_factory() as db:
        return list(
            (
                await db.execute(
                    select(UserFact)
                    .where(
                        UserFact.expires_at.is_not(None),
                        UserFact.expires_at < now,
                    )
                    .order_by(UserFact.expires_at.asc())
                    .limit(_MAX_FACTS)
                )
            ).scalars().all()
        )


async def _load_overdue_commitments(session_factory) -> list[UserCommitment]:
    """Pending commitments past their deadline or too old to keep surfacing."""
    now = datetime.now(UTC)
    stale_cutoff = now - timedelta(days=_COMMITMENT_STALE_DAYS)
    async with session_factory() as db:
        return list(
            (
                await db.execute(
                    select(UserCommitment)
                    .where(
                        UserCommitment.status == "pending",
                        or_(
                            UserCommitment.due_by < now,
                            UserCommitment.created_at < stale_cutoff,
                        ),
                    )
                    .order_by(UserCommitment.created_at.asc())
                    .limit(_MAX_COMMITMENTS)
                )
            ).scalars().all()
        )


# ── Evidence + prompt assembly ───────────────────────────────────────────────


async def _gather_financial_evidence() -> str:
    """Pull real financial data so outcomes are grounded, not guessed.

    Tool failures degrade gracefully — the model is told to mark outcomes
    as unknown when no evidence covers them.
    """
    month = datetime.now(_VN_TZ).strftime("%Y-%m")
    sections: list[str] = []
    for tool_name, args in _EVIDENCE_TOOLS:
        call_args = {"month": month, **args} if tool_name == "get_financial_summary" else args
        try:
            text, is_error = await execute_tool(tool_name, call_args)
            if not is_error and text.strip():
                sections.append(f"[{tool_name}]\n{text}")
        except Exception:
            logger.warning("Dreaming: tool %s failed, skipping", tool_name)
    return "\n\n".join(sections)


def _build_prompt(
    evidence: str,
    facts: list[UserFact],
    commitments: list[UserCommitment],
) -> str:
    parts = [f"Today is {datetime.now(_VN_TZ).strftime('%Y-%m-%d')}."]
    if evidence:
        parts.append(f"<financial_data>\n{evidence}\n</financial_data>")

    if facts:
        lines = ["Expired facts:"]
        for i, f in enumerate(facts, start=1):
            expired = f.expires_at.strftime("%Y-%m-%d") if f.expires_at else "?"
            lines.append(f"{i}. [{f.category}] {f.fact} (expired {expired})")
        parts.append("\n".join(lines))

    if commitments:
        lines = ["Overdue commitments:"]
        for i, c in enumerate(commitments, start=1):
            due = f", due {c.due_by.strftime('%Y-%m-%d')}" if c.due_by else ""
            committed = c.created_at.strftime("%Y-%m-%d") if c.created_at else "?"
            lines.append(f'{i}. "{c.text}" (committed {committed}{due})')
        parts.append("\n".join(lines))

    parts.append(DREAMING_PROMPT)
    return "\n\n".join(parts)


async def _call_dreamer(prompt: str) -> list | None:
    """One structured-model call; returns parsed actions or None on failure."""
    try:
        active_model = await get_structured_model()
        client = anthropic.AsyncAnthropic(**resolve_client_kwargs(active_model))
        response = await client.messages.create(
            model=active_model,
            max_tokens=4000,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = extract_text(response)
        items = json.loads(strip_code_fence(raw_text))
        if not isinstance(items, list):
            logger.warning("Dreaming: expected JSON array, got %s", type(items).__name__)
            return None
        return items
    except json.JSONDecodeError as exc:
        logger.warning("Dreaming: failed to parse JSON — %s", exc)
        return None
    except Exception:
        logger.exception("Dreaming: model call failed")
        return None


# ── Action application ───────────────────────────────────────────────────────


async def _apply_dream_item(
    item: object,
    facts: list[UserFact],
    commitments: list[UserCommitment],
    session_factory,
) -> str:
    """Route one dream action; returns the outcome tag for logging."""
    if not isinstance(item, dict):
        return "skipped"
    action = item.get("action")

    if action == "rewrite":
        row = _pick(facts, item.get("index"))
        text = (item.get("fact") or "").strip() if isinstance(item.get("fact"), str) else ""
        if row is None or not text:
            return "skipped"
        await update_user_fact(
            row.id,
            fact=text,
            category=row.category,
            importance=_clamp_importance(item.get("importance")),
            expires_at=None,  # outcome is evergreen history — survives the purge
            confidence=_clamp_confidence(item.get("confidence")),
            topics=_normalize_topics(item.get("topics"), row.category),
            session_factory=session_factory,
        )
        return "rewritten"

    if action == "drop":
        # No-op by design: purge_expired_facts() deletes it right after.
        return "dropped" if _pick(facts, item.get("index")) else "skipped"

    if action == "resolve_commitment":
        row = _pick(commitments, item.get("index"))
        status = item.get("status")
        if row is None or status not in _RESOLVE_STATUSES:
            return "skipped"
        async with session_factory() as db:
            await db.execute(
                update(UserCommitment)
                .where(UserCommitment.id == row.id)
                .values(status=status, updated_at=datetime.now(UTC))
            )
        return "resolved"

    return "skipped"


def _pick(rows: list, index: object):
    """Resolve a 1-based model-emitted index to a row, or None if invalid."""
    if isinstance(index, bool) or not isinstance(index, int):
        return None
    if not (1 <= index <= len(rows)):
        return None
    return rows[index - 1]
