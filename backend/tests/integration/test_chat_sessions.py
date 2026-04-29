"""Tests for chat session persistence (short/medium-term memory)."""

import uuid

import pytest
from httpx import AsyncClient


# ── Session CRUD ────────────────────────────────────────────────────────────


async def test_create_session_default_title(client: AsyncClient):
    r = await client.post("/api/chat/sessions", json={})
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "New chat"
    assert data["messageCount"] == 0
    assert data["lastMessage"] is None
    assert "id" in data


async def test_create_session_custom_title(client: AsyncClient):
    r = await client.post("/api/chat/sessions", json={"title": "Budget Q2"})
    assert r.status_code == 200
    assert r.json()["title"] == "Budget Q2"


async def test_list_sessions_empty(client: AsyncClient):
    r = await client.get("/api/chat/sessions")
    assert r.status_code == 200
    assert r.json() == []


async def test_list_sessions_returns_created(client: AsyncClient):
    await client.post("/api/chat/sessions", json={"title": "S1"})
    await client.post("/api/chat/sessions", json={"title": "S2"})
    r = await client.get("/api/chat/sessions")
    assert r.status_code == 200
    titles = [s["title"] for s in r.json()]
    assert "S1" in titles
    assert "S2" in titles


async def test_get_session_detail(client: AsyncClient):
    created = (await client.post("/api/chat/sessions", json={"title": "Detail"})).json()
    r = await client.get(f"/api/chat/sessions/{created['id']}")
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Detail"
    assert data["messages"] == []


async def test_get_session_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    r = await client.get(f"/api/chat/sessions/{fake_id}")
    assert r.status_code == 404


async def test_update_session_title(client: AsyncClient):
    created = (await client.post("/api/chat/sessions", json={"title": "Old"})).json()
    r = await client.patch(
        f"/api/chat/sessions/{created['id']}",
        json={"title": "Renamed"},
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Renamed"


async def test_update_session_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    r = await client.patch(f"/api/chat/sessions/{fake_id}", json={"title": "X"})
    assert r.status_code == 404


async def test_delete_session(client: AsyncClient):
    created = (await client.post("/api/chat/sessions", json={"title": "Del"})).json()
    r = await client.delete(f"/api/chat/sessions/{created['id']}")
    assert r.status_code == 200
    assert r.json()["ok"] is True

    # Verify gone
    r2 = await client.get(f"/api/chat/sessions/{created['id']}")
    assert r2.status_code == 404


async def test_delete_session_not_found(client: AsyncClient):
    fake_id = str(uuid.uuid4())
    r = await client.delete(f"/api/chat/sessions/{fake_id}")
    assert r.status_code == 404


# ── Message persistence via DB fixtures ─────────────────────────────────────


async def test_session_with_messages(client: AsyncClient, db):
    """Create a session and manually insert messages, verify detail endpoint."""
    from app.models.chat import ChatMessage, ChatSession

    session = ChatSession(title="With messages")
    db.add(session)
    await db.flush()

    db.add(ChatMessage(session_id=session.id, role="user", content="Tổng chi tháng này?"))
    db.add(ChatMessage(session_id=session.id, role="assistant", content="Tổng chi: 5,000,000 VND"))
    await db.flush()

    r = await client.get(f"/api/chat/sessions/{session.id}")
    assert r.status_code == 200
    data = r.json()
    assert len(data["messages"]) == 2
    assert data["messages"][0]["role"] == "user"
    assert data["messages"][1]["role"] == "assistant"


async def test_delete_session_cascades_messages(client: AsyncClient, db):
    """Deleting a session should remove all its messages."""
    from sqlalchemy import select

    from app.models.chat import ChatMessage, ChatSession

    session = ChatSession(title="Cascade test")
    db.add(session)
    await db.flush()
    sid = session.id

    db.add(ChatMessage(session_id=sid, role="user", content="Hello"))
    db.add(ChatMessage(session_id=sid, role="assistant", content="Hi"))
    await db.flush()

    # Delete via API
    r = await client.delete(f"/api/chat/sessions/{sid}")
    assert r.status_code == 200

    # Messages should be gone
    remaining = (
        await db.execute(select(ChatMessage).where(ChatMessage.session_id == sid))
    ).scalars().all()
    assert remaining == []


async def test_list_sessions_includes_message_count(client: AsyncClient, db):
    """Session list should report correct message_count."""
    from app.models.chat import ChatMessage, ChatSession

    session = ChatSession(title="Count test")
    db.add(session)
    await db.flush()

    for i in range(3):
        db.add(ChatMessage(session_id=session.id, role="user", content=f"msg {i}"))
    await db.flush()

    r = await client.get("/api/chat/sessions")
    assert r.status_code == 200
    found = [s for s in r.json() if s["id"] == str(session.id)]
    assert len(found) == 1
    assert found[0]["messageCount"] == 3
