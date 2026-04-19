"""Chat endpoint — streams AI agent responses via SSE with session persistence."""

import json
import uuid
from datetime import datetime, timedelta, timezone

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
    # Subquery for message count — exclude tool_result rows (empty content, internal-only)
    msg_stats = (
        select(
            ChatMessage.session_id,
            func.count(ChatMessage.id).label("message_count"),
        )
        .where(ChatMessage.content != "")
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
    """Get a session with full blocks so the client can reconstruct thinking/tool timeline.

    Tool-result rows are included verbatim — the client maps them onto each
    tool_use block by tool_use_id so every prior assistant turn shows its
    thinking, tool calls, and outputs, not just the final text.
    """
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


def _db_rows_to_claude_messages(rows: list[ChatMessage]) -> list[dict]:
    """Convert persisted chat rows to Anthropic Messages API format.

    - If `blocks` is present, use it verbatim (full fidelity: tool_use, tool_result,
      thinking with signature, text).
    - Otherwise fall back to plain `content` string (legacy rows and simple text).
    """
    messages: list[dict] = []
    for row in rows:
        if row.blocks:
            messages.append({"role": row.role, "content": row.blocks})
        elif row.content:
            messages.append({"role": row.role, "content": row.content})
    return messages


def _parse_sse(event: str) -> tuple[str, dict]:
    """Extract (event_name, data) from an SSE-formatted string."""
    name = ""
    data: dict = {}
    for line in event.split("\n"):
        if line.startswith("event: "):
            name = line[7:].strip()
        elif line.startswith("data: "):
            try:
                data = json.loads(line[6:])
            except json.JSONDecodeError:
                data = {}
    return name, data


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    """Stream AI agent response as SSE events, persisting full Anthropic blocks.

    History reconstruction uses the DB as source of truth: every assistant
    iteration (text + thinking + tool_use) and every tool_results batch is
    stored as its own row so follow-up turns see the exact prior conversation,
    tool calls included.
    """
    from app.mcp.db import get_session

    # Resolve or create session + persist the new user message
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

        latest_user = request.messages[-1] if request.messages else None
        if latest_user and latest_user.role == "user":
            db.add(ChatMessage(
                session_id=session_id,
                role="user",
                content=latest_user.content,
            ))
            if session.title == "New chat":
                session.title = latest_user.content[:100]

    # Load canonical history from DB (includes the just-saved user message)
    async with get_session() as load_db:
        result = await load_db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at, ChatMessage.id)
        )
        rows = list(result.scalars().all())
    messages = _db_rows_to_claude_messages(rows)

    async def stream_and_save():
        """Forward SSE events and persist every assistant + tool_results message."""
        pending_rows: list[ChatMessage] = []
        collected_final_text = ""

        async for event in run_agent_stream(messages):
            name, data = _parse_sse(event)

            if name == "_persist_assistant":
                blocks = data.get("blocks") or []
                # Extract text portion for quick display / non-block consumers
                text_parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
                text = "".join(text_parts)
                pending_rows.append(ChatMessage(
                    session_id=session_id,
                    role="assistant",
                    content=text,
                    blocks=blocks,
                ))
                # The last assistant message with no subsequent tool call carries the final answer
                collected_final_text = text
                continue  # internal event — don't forward to client

            if name == "_persist_tool_results":
                blocks = data.get("blocks") or []
                pending_rows.append(ChatMessage(
                    session_id=session_id,
                    role="user",
                    content="",
                    blocks=blocks,
                ))
                continue  # internal event — don't forward to client

            yield event

            if name == "done":
                if pending_rows:
                    # Assign monotonically increasing timestamps so load-order is
                    # deterministic. Postgres `now()` is transaction-constant, so
                    # relying on server_default would collapse all rows to the same
                    # instant and a later UUID tiebreak would scramble tool_use/
                    # tool_result pairing — Claude rejects that with a 400.
                    base_time = datetime.now(timezone.utc)
                    async with get_session() as save_db:
                        for i, row in enumerate(pending_rows):
                            row.created_at = base_time + timedelta(microseconds=i)
                            save_db.add(row)
                        result = await save_db.execute(
                            select(ChatSession).where(ChatSession.id == session_id)
                        )
                        s = result.scalar_one_or_none()
                        if s:
                            s.updated_at = base_time + timedelta(
                                microseconds=len(pending_rows),
                            )

                if collected_final_text.strip():
                    # Review only needs plain text — skip tool_result blocks and raw tool_use JSON
                    text_history = [
                        {"role": r.role, "content": r.content}
                        for r in rows
                        if r.content
                    ]
                    await maybe_trigger_review(session_id, text_history + [
                        {"role": "assistant", "content": collected_final_text},
                    ])

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
