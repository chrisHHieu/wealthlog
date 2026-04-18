"""Chat endpoint — streams AI agent responses via SSE with session persistence."""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.chat import ChatMessage, ChatSession
from app.schemas.chat import (
    ChatRequest,
    SessionCreate,
    SessionDetailResponse,
    SessionResponse,
    SessionUpdate,
)
from app.services.agent import run_agent_stream
from app.services.memory import maybe_trigger_review

router = APIRouter(prefix="/api", tags=["chat"])


# ── Sessions CRUD ────────────────────────────────────────────────────────────


@router.get("/chat/sessions", response_model=list[SessionResponse])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """List all chat sessions, most recent first."""
    # Subquery for message count and last message
    msg_stats = (
        select(
            ChatMessage.session_id,
            func.count(ChatMessage.id).label("message_count"),
            func.max(ChatMessage.content).label("last_message"),
        )
        .group_by(ChatMessage.session_id)
        .subquery()
    )

    rows = (
        await db.execute(
            select(
                ChatSession,
                func.coalesce(msg_stats.c.message_count, 0).label("message_count"),
            )
            .outerjoin(msg_stats, ChatSession.id == msg_stats.c.session_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(50)
        )
    ).all()

    results = []
    for row in rows:
        session = row[0]
        count = row[1]
        # Get last user message for preview
        last_msg = await db.execute(
            select(ChatMessage.content)
            .where(ChatMessage.session_id == session.id, ChatMessage.role == "user")
            .order_by(ChatMessage.created_at.desc())
            .limit(1)
        )
        last = last_msg.scalar_one_or_none()
        results.append(SessionResponse(
            id=session.id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=count,
            last_message=last[:100] if last else None,
        ))

    return results


@router.post("/chat/sessions", response_model=SessionResponse)
async def create_session(
    body: SessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat session."""
    session = ChatSession(title=body.title)
    db.add(session)
    await db.flush()
    return SessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        message_count=0,
        last_message=None,
    )


@router.get("/chat/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a session with all its messages."""
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionDetailResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at,
            }
            for m in session.messages
        ],
    )


@router.patch("/chat/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: uuid.UUID,
    body: SessionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update session title."""
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.title = body.title
    await db.flush()
    await db.refresh(session)
    return SessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.delete("/chat/sessions/{session_id}")
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a session and all its messages."""
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await db.delete(session)
    return {"ok": True}


# ── Chat (SSE streaming) ────────────────────────────────────────────────────


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Stream AI agent response as SSE events.

    If session_id is provided, messages are persisted to that session.
    If not, a new session is auto-created.

    Uses standalone DB sessions (not FastAPI DI) because streaming
    continues after the request handler returns.
    """
    from app.mcp.db import get_session

    # Resolve or create session, commit immediately so FK is available
    async with get_session() as db:
        session_id = request.session_id
        if session_id:
            result = await db.execute(
                select(ChatSession).where(ChatSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            if not session:
                session = ChatSession(id=session_id)
                db.add(session)
        else:
            session = ChatSession()
            db.add(session)
            await db.flush()
            session_id = session.id

        # Save the latest user message
        latest_user = request.messages[-1] if request.messages else None
        if latest_user and latest_user.role == "user":
            db.add(ChatMessage(
                session_id=session_id,
                role="user",
                content=latest_user.content,
            ))

            # Auto-title from first user message
            if session.title == "New chat":
                session.title = latest_user.content[:100]

    # Session is now committed — safe for FK references

    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    async def stream_and_save():
        """Wrap agent stream to capture and save the assistant response."""
        collected_text = ""
        async for event in run_agent_stream(messages):
            # Capture text deltas for persistence
            if event.startswith("event: text_delta"):
                lines = event.split("\n")
                for line in lines:
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        collected_text += data.get("text", "")

            yield event

            # On done event, save assistant message
            if event.startswith("event: done"):
                if collected_text.strip():
                    async with get_session() as save_db:
                        save_db.add(ChatMessage(
                            session_id=session_id,
                            role="assistant",
                            content=collected_text,
                        ))
                        # Update session timestamp
                        result = await save_db.execute(
                            select(ChatSession).where(ChatSession.id == session_id)
                        )
                        s = result.scalar_one_or_none()
                        if s:
                            s.updated_at = datetime.now(timezone.utc)

                    # Trigger background review
                    await maybe_trigger_review(session_id, messages + [
                        {"role": "assistant", "content": collected_text},
                    ])

    # Include session_id in the first SSE event so frontend knows it
    async def stream_with_session_id():
        yield f"event: session\ndata: {json.dumps({'session_id': str(session_id)})}\n\n"
        async for event in stream_and_save():
            yield event

    return StreamingResponse(
        stream_with_session_id(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
