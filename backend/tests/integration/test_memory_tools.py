"""Integration tests for the user-facing memory MCP tools."""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_fact import UserFact


@pytest.fixture
def patch_session(db: AsyncSession):
    """Route every get_session() call in the memory layer to the test DB."""

    @asynccontextmanager
    async def _patched():
        yield db

    # Both modules open their own get_session blocks; patch both so the
    # short-id resolver and the CRUD calls land on the same SQLite session.
    patches = [
        patch("app.ai.mcp.tools.memory.get_session", _patched),
        patch("app.ai.memory.facts.get_session", _patched),
    ]
    for p in patches:
        p.start()
    yield
    for p in patches:
        p.stop()


async def _call_tool(name: str, **kwargs) -> str:
    """Invoke a registered MCP tool by name and return its text output."""
    from app.ai.mcp.server import mcp

    result = await mcp.call_tool(name, kwargs)
    # FastMCP wraps the return value in a list of TextContent — flatten to plain str.
    if isinstance(result, list):
        return "\n".join(getattr(c, "text", str(c)) for c in result)
    if isinstance(result, tuple):
        # FastMCP >=1.10 returns (content, structured) — the first element is what we want.
        content, _structured = result
        return "\n".join(getattr(c, "text", str(c)) for c in content)
    return str(result)


# ── list_my_facts ──────────────────────────────────────────────────────────


async def test_list_my_facts_empty(db, patch_session):
    out = await _call_tool("list_my_facts")
    assert "No facts" in out


async def test_list_my_facts_shows_short_id_and_verified_marker(db, patch_session):
    db.add(UserFact(
        fact="confirmed goal", category="goal", importance=8,
        verified_by_user=True,
    ))
    db.add(UserFact(
        fact="reviewer guess", category="goal", importance=8,
        verified_by_user=False,
    ))
    await db.flush()

    out = await _call_tool("list_my_facts")
    assert "[✓]" in out  # verified marker present
    assert "confirmed goal" in out
    assert "reviewer guess" in out
    # Short ID = first 8 chars of UUID (no hyphens). Hard to assert exact
    # value, but every printed line should carry one.
    for line in out.splitlines()[1:]:
        token = line.lstrip("- ").split(" ", 1)[0]
        assert len(token) == 8 and all(c in "0123456789abcdef" for c in token)


async def test_list_my_facts_paginates_with_offset(db, patch_session):
    """A truncated first page must be continuable — offset reaches the tail."""
    for i in range(5):
        db.add(UserFact(fact=f"fact {i}", category="general", importance=10 - i))
    await db.flush()

    page1 = await _call_tool("list_my_facts", limit=2)
    assert page1.startswith("Facts 1–2 of 5:")
    assert "fact 0" in page1 and "fact 1" in page1
    assert "re-call with offset=2" in page1

    page2 = await _call_tool("list_my_facts", limit=2, offset=2)
    assert page2.startswith("Facts 3–4 of 5:")
    assert "fact 2" in page2 and "fact 3" in page2
    assert "fact 0" not in page2  # no overlap with page 1

    last = await _call_tool("list_my_facts", limit=2, offset=4)
    assert last.startswith("Facts 5–5 of 5:")
    assert "re-call with offset" not in last  # nothing further to page

    beyond = await _call_tool("list_my_facts", limit=2, offset=10)
    assert "only 5 stored" in beyond


async def test_list_my_facts_does_not_bump_access_count(db, patch_session):
    """Listing is introspection — it must not pollute the recency tie-breaker."""
    db.add(UserFact(fact="x", category="general", importance=5))
    await db.flush()

    await _call_tool("list_my_facts")

    row = (await db.execute(select(UserFact))).scalar_one()
    assert row.access_count == 0
    assert row.last_accessed_at is None


# ── forget_fact ────────────────────────────────────────────────────────────


async def test_forget_fact_by_short_prefix(db, patch_session):
    row = UserFact(fact="to delete", category="general", importance=5)
    db.add(row)
    await db.flush()
    short = str(row.id).replace("-", "")[:8]

    out = await _call_tool("forget_fact", fact_id=short)
    assert "Forgotten" in out
    remaining = (await db.execute(select(UserFact))).scalars().all()
    assert remaining == []


async def test_forget_fact_unknown_id_returns_clear_error(db, patch_session):
    out = await _call_tool("forget_fact", fact_id="deadbeef")
    assert "No fact matches" in out


async def test_forget_fact_ambiguous_prefix_refuses(db, patch_session):
    """Two facts whose IDs share a prefix can't both be matched by the prefix."""
    shared = uuid.uuid4().hex[:6]
    a = UserFact(
        id=uuid.UUID(shared + "0" * 26), fact="a",
        category="general", importance=5,
    )
    b = UserFact(
        id=uuid.UUID(shared + "1" * 26), fact="b",
        category="general", importance=5,
    )
    db.add(a)
    db.add(b)
    await db.flush()

    out = await _call_tool("forget_fact", fact_id=shared)
    assert "No fact matches" in out
    rows = (await db.execute(select(UserFact))).scalars().all()
    assert len(rows) == 2  # neither was deleted


# ── edit_fact ──────────────────────────────────────────────────────────────


async def test_edit_fact_updates_text_only(db, patch_session):
    row = UserFact(
        fact="50tr", category="goal", importance=7, verified_by_user=True,
    )
    db.add(row)
    await db.flush()
    original_id = row.id
    short = str(row.id).replace("-", "")[:8]

    out = await _call_tool("edit_fact", fact_id=short, fact="80tr")
    assert "Updated" in out

    refreshed = (await db.execute(select(UserFact))).scalar_one()
    assert refreshed.id == original_id  # identity preserved
    assert refreshed.fact == "80tr"
    assert refreshed.category == "goal"  # unchanged
    assert refreshed.importance == 7  # unchanged
    assert refreshed.verified_by_user is True  # untouched by edit


async def test_edit_fact_rejects_invalid_category(db, patch_session):
    row = UserFact(fact="x", category="general", importance=5)
    db.add(row)
    await db.flush()
    short = str(row.id).replace("-", "")[:8]

    out = await _call_tool(
        "edit_fact", fact_id=short, fact="x", category="bogus",
    )
    assert "Invalid category" in out
    refreshed = (await db.execute(select(UserFact))).scalar_one()
    assert refreshed.fact == "x"  # untouched


async def test_edit_fact_rejects_empty_text(db, patch_session):
    row = UserFact(fact="x", category="general", importance=5)
    db.add(row)
    await db.flush()
    short = str(row.id).replace("-", "")[:8]

    out = await _call_tool("edit_fact", fact_id=short, fact="   ")
    assert "cannot be empty" in out


# ── verify_fact ────────────────────────────────────────────────────────────


async def test_verify_fact_sets_flag(db, patch_session):
    row = UserFact(
        fact="confirmed by user", category="goal", importance=7,
        verified_by_user=False,
    )
    db.add(row)
    await db.flush()
    short = str(row.id).replace("-", "")[:8]

    out = await _call_tool("verify_fact", fact_id=short)
    assert "Verified" in out
    refreshed = (await db.execute(select(UserFact))).scalar_one()
    assert refreshed.verified_by_user is True


async def test_verify_fact_idempotent(db, patch_session):
    row = UserFact(
        fact="already done", category="goal", importance=7,
        verified_by_user=True,
    )
    db.add(row)
    await db.flush()
    short = str(row.id).replace("-", "")[:8]

    out = await _call_tool("verify_fact", fact_id=short)
    assert "Already verified" in out
