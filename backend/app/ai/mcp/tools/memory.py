"""MCP tools for user-facing memory control (facts + commitments)."""

import uuid
from datetime import UTC, datetime

from mcp.server.fastmcp import FastMCP
from sqlalchemy import or_, select

from app.ai.memory.commitments import update_commitment_status
from app.ai.memory.facts import (
    _VALID_CATEGORIES,
    delete_user_fact,
    update_user_fact,
)
from app.database import get_session
from app.models.user_commitment import UserCommitment
from app.models.user_fact import UserFact

_ID_PREFIX_LEN = 8

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


# ── Shared helpers ────────────────────────────────────────────────────────────


def _short_id(row_id: uuid.UUID) -> str:
    return str(row_id).replace("-", "")[:_ID_PREFIX_LEN]


async def _resolve_fact_id(prefix: str) -> uuid.UUID | None:
    """Expand a short fact-ID prefix to a full UUID, or None on miss/ambiguity."""
    cleaned = prefix.strip().replace("-", "").lower()
    if not cleaned:
        return None
    try:
        return uuid.UUID(cleaned)
    except ValueError:
        pass
    async with get_session() as db:
        rows = (await db.execute(select(UserFact.id))).scalars().all()
    matches = [r for r in rows if str(r).replace("-", "").startswith(cleaned)]
    return matches[0] if len(matches) == 1 else None


async def _resolve_commitment_id(prefix: str) -> uuid.UUID | None:
    """Expand a short commitment-ID prefix to a full UUID, or None on miss/ambiguity."""
    cleaned = prefix.strip().replace("-", "").lower()
    if not cleaned:
        return None
    try:
        return uuid.UUID(cleaned)
    except ValueError:
        pass
    async with get_session() as db:
        rows = (await db.execute(select(UserCommitment.id))).scalars().all()
    matches = [r for r in rows if str(r).replace("-", "").startswith(cleaned)]
    return matches[0] if len(matches) == 1 else None


# ── Tool registration ─────────────────────────────────────────────────────────


def register(mcp: FastMCP) -> None:

    # ── Fact tools ────────────────────────────────────────────────────────────

    @mcp.tool()
    async def list_my_facts(limit: int = 50) -> str:
        """Show every long-term fact currently remembered about the user.
        - limit: max rows to return (default 50, max 200).

        NOTE: Facts are already injected into your system prompt context — do NOT
        call this to look up what you know. Call ONLY when the user explicitly asks
        to see/manage their stored facts, or when you need a short ID to call
        forget_fact or edit_fact."""
        capped = max(1, min(limit, 200))
        async with get_session() as db:
            rows = (
                await db.execute(
                    select(UserFact)
                    .where(
                        or_(
                            UserFact.expires_at.is_(None),
                            UserFact.expires_at > datetime.now(UTC),
                        )
                    )
                    .order_by(
                        UserFact.importance.desc(),
                        UserFact.verified_by_user.desc(),
                        UserFact.updated_at.desc(),
                    )
                    .limit(capped)
                )
            ).scalars().all()

        if not rows:
            return "No facts stored yet."

        lines = [f"{len(rows)} fact(s):"]
        for r in rows:
            label = _CATEGORY_LABELS.get(r.category, r.category)
            mark = "[✓]" if r.verified_by_user else "   "
            topics_str = f" [{', '.join(r.topics)}]" if r.topics else ""
            lines.append(
                f"- {_short_id(r.id)} {mark} ({label}, importance={r.importance}) "
                f"{r.fact}{topics_str}"
            )
        return "\n".join(lines)

    @mcp.tool()
    async def forget_fact(fact_id: str) -> str:
        """Permanently delete one stored fact by its short ID.
        - fact_id: short prefix (first 8 chars from list_my_facts) or full UUID.

        Use when the user asks to forget something specific."""
        resolved = await _resolve_fact_id(fact_id)
        if resolved is None:
            return f"No fact matches '{fact_id}'. Run list_my_facts to see current IDs."
        ok = await delete_user_fact(resolved)
        if not ok:
            return f"Fact {fact_id} no longer exists (already deleted?)."
        return f"Forgotten: {_short_id(resolved)}."

    @mcp.tool()
    async def edit_fact(
        fact_id: str,
        fact: str,
        category: str | None = None,
        importance: int | None = None,
    ) -> str:
        """Replace the text (and optionally category / importance) of a stored fact.
        - fact_id: short prefix or full UUID from list_my_facts.
        - fact: new text (required).
        - category: preference | habit | goal | context | pattern | commitment |
                    emotion | general (optional).
        - importance: 1-10 (optional).

        Use when the user corrects something captured wrong, e.g.
        'actually my goal is 80M not 50M'."""
        resolved = await _resolve_fact_id(fact_id)
        if resolved is None:
            return f"No fact matches '{fact_id}'."

        new_text = fact.strip()
        if not new_text:
            return "fact text cannot be empty."

        async with get_session() as db:
            row = (
                await db.execute(select(UserFact).where(UserFact.id == resolved))
            ).scalar_one_or_none()
        if row is None:
            return f"Fact {fact_id} no longer exists."

        new_category = category or row.category
        if new_category not in _VALID_CATEGORIES:
            return (
                f"Invalid category '{new_category}'. "
                f"Allowed: {', '.join(_VALID_CATEGORIES)}."
            )
        new_importance = importance if importance is not None else row.importance
        if not (1 <= new_importance <= 10):
            return "importance must be between 1 and 10."

        ok = await update_user_fact(
            fact_id=resolved,
            fact=new_text,
            category=new_category,
            importance=new_importance,
            expires_at=row.expires_at,
        )
        return "Updated." if ok else "Update failed."

    @mcp.tool()
    async def verify_fact(fact_id: str) -> str:
        """Mark a stored fact as user-verified (the user confirmed it is correct).
        - fact_id: short prefix or full UUID from list_my_facts.

        Verified facts rank above unverified ones. Call when the user explicitly
        confirms something ('yes, my goal really is 80M')."""
        resolved = await _resolve_fact_id(fact_id)
        if resolved is None:
            return f"No fact matches '{fact_id}'."
        async with get_session() as db:
            row = (
                await db.execute(select(UserFact).where(UserFact.id == resolved))
            ).scalar_one_or_none()
            if row is None:
                return f"Fact {fact_id} no longer exists."
            if row.verified_by_user:
                return f"Already verified: {_short_id(resolved)}."
            row.verified_by_user = True
        return f"Verified: {_short_id(resolved)}."

    # ── Commitment tools ──────────────────────────────────────────────────────

    @mcp.tool()
    async def list_commitments(include_resolved: bool = False) -> str:
        """Show commitments the user has made (things they said they would do).
        - include_resolved: if True, also show done/abandoned ones (default False).

        Use when the user asks about their pending commitments or to-dos."""
        async with get_session() as db:
            stmt = select(UserCommitment).order_by(UserCommitment.created_at.asc())
            if not include_resolved:
                stmt = stmt.where(UserCommitment.status == "pending")
            rows = (await db.execute(stmt)).scalars().all()

        if not rows:
            label = "pending commitments" if not include_resolved else "commitments"
            return f"No {label} found."

        lines = [f"{len(rows)} commitment(s):"]
        for r in rows:
            age = (datetime.now(UTC) - (
                r.created_at.replace(tzinfo=UTC)
                if r.created_at.tzinfo is None else r.created_at
            )).days
            age_str = "today" if age == 0 else f"{age}d ago"
            status_marker = {"pending": "⏳", "done": "✅", "abandoned": "❌"}.get(
                r.status, r.status
            )
            lines.append(
                f"- {_short_id(r.id)} {status_marker} \"{r.text}\" (said {age_str})"
            )
        return "\n".join(lines)

    @mcp.tool()
    async def complete_commitment(commitment_id: str) -> str:
        """Mark a commitment as done — the user followed through.
        - commitment_id: short prefix (first 8 chars from list_commitments) or full UUID.

        Call this when the user confirms they completed something they said they'd do."""
        resolved = await _resolve_commitment_id(commitment_id)
        if resolved is None:
            return f"No commitment matches '{commitment_id}'. Run list_commitments to see IDs."
        ok = await update_commitment_status(resolved, "done")
        return f"Marked done: {_short_id(resolved)}." if ok else "Commitment not found."

    @mcp.tool()
    async def dismiss_commitment(commitment_id: str) -> str:
        """Mark a commitment as abandoned — the user decided not to follow through.
        - commitment_id: short prefix (first 8 chars from list_commitments) or full UUID.

        Call this when the user says they're no longer planning to do something."""
        resolved = await _resolve_commitment_id(commitment_id)
        if resolved is None:
            return f"No commitment matches '{commitment_id}'. Run list_commitments to see IDs."
        ok = await update_commitment_status(resolved, "abandoned")
        return f"Dismissed: {_short_id(resolved)}." if ok else "Commitment not found."
