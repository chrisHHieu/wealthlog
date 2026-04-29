"""MCP tools for user-facing memory control (list / forget / edit / verify)."""

import uuid
from datetime import UTC, datetime

from mcp.server.fastmcp import FastMCP
from sqlalchemy import or_, select

from app.ai.memory.facts import (
    _VALID_CATEGORIES,
    delete_user_fact,
    update_user_fact,
)
from app.database import get_session
from app.models.user_fact import UserFact

# UUIDs are 36 chars — too noisy in chat. The first 8 hex chars carry
# enough entropy to disambiguate within a single user's fact set, and the
# resolver expands a prefix back to a full ID before any DB write.
_ID_PREFIX_LEN = 8

_CATEGORY_LABELS = {
    "preference": "Preference",
    "habit": "Habit",
    "goal": "Goal",
    "context": "Context",
    "general": "General",
}


def _short_id(fact_id: uuid.UUID) -> str:
    return str(fact_id).replace("-", "")[:_ID_PREFIX_LEN]


async def _resolve_id(prefix: str) -> uuid.UUID | None:
    """Expand a short ID prefix to a full UUID, or return None on miss/ambiguity.

    User-facing IDs are 8-char prefixes; we only commit a destructive op when
    the prefix uniquely identifies one row, so a typo can't accidentally hit
    the wrong fact.
    """
    cleaned = prefix.strip().replace("-", "").lower()
    if not cleaned:
        return None
    try:
        # Full UUID provided — bypass the prefix lookup entirely.
        return uuid.UUID(cleaned)
    except ValueError:
        pass

    async with get_session() as db:
        rows = (await db.execute(select(UserFact.id))).scalars().all()
    matches = [
        rid for rid in rows if str(rid).replace("-", "").startswith(cleaned)
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def register(mcp: FastMCP) -> None:
    @mcp.tool()
    async def list_my_facts(limit: int = 50) -> str:
        """Show every long-term fact the assistant currently remembers about the user.
        - limit: max rows to return (default 50, max 200).

        Use this whenever the user asks "what do you know about me?" or wants
        to audit / clean up stored facts before calling forget_fact / edit_fact."""
        # Read-only introspection — disable access tracking so listing facts
        # does not pollute the recency-based tie-breaker.
        capped = max(1, min(limit, 200))
        async with get_session() as db:
            rows = (await db.execute(
                select(UserFact)
                .where(or_(
                    UserFact.expires_at.is_(None),
                    UserFact.expires_at > datetime.now(UTC),
                ))
                .order_by(
                    UserFact.importance.desc(),
                    UserFact.verified_by_user.desc(),
                    UserFact.updated_at.desc(),
                )
                .limit(capped)
            )).scalars().all()

        if not rows:
            return "No facts stored yet."

        lines = [f"{len(rows)} fact(s):"]
        for r in rows:
            label = _CATEGORY_LABELS.get(r.category, r.category)
            mark = "[✓]" if r.verified_by_user else "   "
            lines.append(
                f"- {_short_id(r.id)} {mark} ({label}, importance={r.importance}) "
                f"{r.fact}"
            )
        return "\n".join(lines)

    @mcp.tool()
    async def forget_fact(fact_id: str) -> str:
        """Permanently delete one stored fact by its short ID (first 8 chars from list_my_facts).
        - fact_id: short prefix or full UUID.

        Use this when the user asks the assistant to forget something specific
        ("quên đi mục tiêu mua xe" / "forget the car goal")."""
        resolved = await _resolve_id(fact_id)
        if resolved is None:
            return (
                f"No fact matches '{fact_id}'. Run list_my_facts to see "
                f"current IDs."
            )
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
        - category: preference | habit | goal | context | general (optional).
        - importance: 1-10 (optional).

        Use when the user corrects something the reviewer captured wrong, e.g.
        "actually my goal is 80M not 50M". Preserves the row's history (id,
        access stats, verified flag); does not reset confidence."""
        resolved = await _resolve_id(fact_id)
        if resolved is None:
            return f"No fact matches '{fact_id}'."

        new_text = fact.strip()
        if not new_text:
            return "fact text cannot be empty."

        async with get_session() as db:
            row = (await db.execute(
                select(UserFact).where(UserFact.id == resolved)
            )).scalar_one_or_none()
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
            # confidence intentionally omitted — the user is the source of
            # truth here, but verifying the text is a separate action.
        )
        return "Updated." if ok else "Update failed."

    @mcp.tool()
    async def verify_fact(fact_id: str) -> str:
        """Mark a stored fact as user-verified — i.e. the user has confirmed it is correct.
        - fact_id: short prefix or full UUID from list_my_facts.

        Verified facts rank above unverified ones at equal importance, so the
        agent leans on them more confidently. Call this when the user explicitly
        confirms something ("yes, my goal really is 80M")."""
        resolved = await _resolve_id(fact_id)
        if resolved is None:
            return f"No fact matches '{fact_id}'."
        async with get_session() as db:
            row = (await db.execute(
                select(UserFact).where(UserFact.id == resolved)
            )).scalar_one_or_none()
            if row is None:
                return f"Fact {fact_id} no longer exists."
            if row.verified_by_user:
                return f"Already verified: {_short_id(resolved)}."
            row.verified_by_user = True
        return f"Verified: {_short_id(resolved)}."
