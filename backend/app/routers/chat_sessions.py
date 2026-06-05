"""Chat session CRUD endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api_errors import not_found
from app.database import get_db
from app.models.chat import ChatMessage, ChatSession
from app.schemas.ai.chat import (
    SessionCreate,
    SessionDetailResponse,
    SessionResponse,
    SessionUpdate,
)

router = APIRouter(prefix="/api", tags=["chat"])


@router.get("/chat/sessions", response_model=list[SessionResponse])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """List all chat sessions, most recent first."""
    # Count user turns only (content != "" excludes tool_result rows).
    msg_stats = (
        select(
            ChatMessage.session_id,
            func.count(ChatMessage.id).label("message_count"),
        )
        .where(ChatMessage.content != "")
        .group_by(ChatMessage.session_id)
        .subquery()
    )

    last_user_message = (
        select(ChatMessage.content)
        .where(ChatMessage.session_id == ChatSession.id, ChatMessage.role == "user")
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(1)
        .scalar_subquery()
    )

    rows = (
        await db.execute(
            select(
                ChatSession,
                func.coalesce(msg_stats.c.message_count, 0).label("message_count"),
                last_user_message.label("last_message"),
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
        last = row[2]
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
    """Get a session with full blocks for client timeline reconstruction."""
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise not_found("Session not found")

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
                "blocks": m.blocks,
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
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise not_found("Session not found")

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
    result = await db.execute(select(ChatSession).where(ChatSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise not_found("Session not found")

    await db.delete(session)
    return {"ok": True}
