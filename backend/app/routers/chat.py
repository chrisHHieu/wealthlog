"""Chat endpoint — streams AI agent responses via SSE with session persistence."""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.chat import ChatMessage, ChatSession
from app.schemas.ai.chat import (
    ChatRequest,
    SessionCreate,
    SessionDetailResponse,
    SessionResponse,
    SessionUpdate,
)
from app.ai.agent import run_agent_stream
from app.ai.memory.episodic import maybe_summarize_stale_sessions
from app.ai.memory.facts import maybe_trigger_review
from app.ai.memory.synthesis import maybe_synthesize_user_model

router = APIRouter(prefix="/api", tags=["chat"])


# ── In-memory registry of active agent runs ─────────────────────────────────
#
# Lets a refreshed/navigated client reconnect to an in-progress stream and pick
# up live events instead of seeing only what's already in the DB. The buffer
# only holds events for the CURRENT iteration — once `_persist_assistant`
# fires for an iteration its blocks are in the DB, so replaying buffered
# events for it would cause duplicates on the client.

@dataclass
class _RunState:
    current_iteration_events: list[str] = field(default_factory=list)
    subscribers: list[asyncio.Queue] = field(default_factory=list)
    done: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def emit(self, event: str, name: str) -> None:
        async with self.lock:
            if name == "iteration":
                self.current_iteration_events = [event]
            else:
                self.current_iteration_events.append(event)
            subs = list(self.subscribers)
        for q in subs:
            await q.put(event)

    async def reset_iteration_buffer(self) -> None:
        async with self.lock:
            self.current_iteration_events = []

    async def finish(self) -> None:
        async with self.lock:
            self.done = True
            subs = list(self.subscribers)
            self.subscribers.clear()
        for q in subs:
            await q.put(None)

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        async with self.lock:
            for ev in self.current_iteration_events:
                q.put_nowait(ev)
            if self.done:
                q.put_nowait(None)
            else:
                self.subscribers.append(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue) -> None:
        async with self.lock:
            try:
                self.subscribers.remove(q)
            except ValueError:
                pass


_active_runs: dict[uuid.UUID, _RunState] = {}
_RUN_CLEANUP_GRACE_SECONDS = 60


# ── Sessions CRUD ────────────────────────────────────────────────────────────


@router.get("/chat/sessions", response_model=list[SessionResponse])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """List all chat sessions, most recent first."""
    # Count user turns only (content != "" excludes tool_result rows).
    # Multiply by 2 for display: each user turn = 1 question + 1 assistant reply.
    # Counting raw assistant rows is unreliable — DeepSeek emits text alongside
    # tool_use blocks, producing extra non-empty assistant rows per iteration.
    msg_stats = (
        select(
            ChatMessage.session_id,
            (func.count(ChatMessage.id) * 2).label("message_count"),
        )
        .where(ChatMessage.role == "user", ChatMessage.content != "")
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


# ── Model catalogue ─────────────────────────────────────────────────────────

_ANTHROPIC_MODELS = [
    {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "description": "Cân bằng tốc độ và chất lượng"},
]

_DEEPSEEK_MODELS = [
    {"id": "deepseek-v4-pro", "name": "DeepSeek V4 Pro", "description": "Mạnh, chi phí thấp hơn Claude"},
]


@router.get("/chat/models")
async def list_models():
    """Return all available models. DeepSeek models appear only when DEEPSEEK_API_KEY is set."""
    from app.ai.model_registry import get_preferred_model
    from app.config import settings
    models = list(_ANTHROPIC_MODELS)
    if settings.deepseek_api_key:
        models += _DEEPSEEK_MODELS
    preferred = await get_preferred_model()
    return {"models": models, "default": preferred}


@router.put("/chat/models/preferred")
async def set_preferred_model(body: dict):
    """Persist the user's preferred model so all AI features use it."""
    from app.ai.model_registry import set_preferred_model as _set
    model_id = body.get("model")
    if not model_id or not isinstance(model_id, str):
        raise HTTPException(status_code=400, detail="Missing 'model' field")
    await _set(model_id)
    return {"ok": True, "model": model_id}


# ── Chat (SSE streaming) ────────────────────────────────────────────────────


def _db_rows_to_claude_messages(
    rows: list[ChatMessage],
    active_model: str,
) -> list[dict]:
    """Convert persisted chat rows to Anthropic Messages API format.

    Thinking blocks are stripped when:
    - The active model doesn't support thinking at all, OR
    - The row was produced by a different provider (signatures are not
      cross-compatible between Claude and DeepSeek).

    When thinking is stripped from an assistant turn that also has tool_use,
    the tool_use blocks are removed too — Claude rejects assistant[tool_use]
    without an accompanying thinking block when thinking mode is enabled.
    The corresponding tool_result user rows are also skipped to keep the
    conversation structurally valid (no orphan tool_results).
    """
    from app.ai.model_registry import get_provider, supports_thinking
    active_provider = get_provider(active_model)
    model_supports_thinking = supports_thinking(active_model)

    # tool_use IDs whose thinking was stripped — matching tool_result rows are skipped.
    orphaned_tool_ids: set[str] = set()
    messages: list[dict] = []

    for row in rows:
        if row.blocks:
            blocks: list[dict] = row.blocks

            # Skip tool_result rows that reference orphaned tool_use IDs.
            if orphaned_tool_ids and all(b.get("type") == "tool_result" for b in blocks):
                result_ids = {b.get("tool_use_id") for b in blocks}
                if result_ids & orphaned_tool_ids:
                    orphaned_tool_ids -= result_ids
                    continue

            row_provider = get_provider(row.model) if row.model else None
            should_strip = (
                not model_supports_thinking
                or (row_provider is not None and row_provider != active_provider)
            )
            if should_strip:
                # Track tool_use IDs being removed so their tool_results are skipped.
                for b in blocks:
                    if b.get("type") == "tool_use":
                        orphaned_tool_ids.add(b["id"])
                blocks = [
                    b for b in blocks
                    if b.get("type") not in ("thinking", "tool_use")
                ]
                if not blocks:
                    continue

            messages.append({"role": row.role, "content": blocks})
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
    from app.database import get_session

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

    # Fire-and-forget: backfill summaries for other idle sessions so the next
    # system prompt can reference them. Current session is excluded — we never
    # summarize a live conversation mid-turn.
    asyncio.create_task(maybe_summarize_stale_sessions(exclude_session_id=session_id))

    # Load canonical history from DB (includes the just-saved user message).
    # Thinking blocks from a different provider are stripped automatically
    # inside _db_rows_to_claude_messages — signatures are not cross-compatible.
    from app.ai.model_registry import get_preferred_model
    active_model = request.model or await get_preferred_model()
    async with get_session() as load_db:
        result = await load_db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at, ChatMessage.id)
        )
        rows = list(result.scalars().all())
    messages = _db_rows_to_claude_messages(rows, active_model=active_model)

    # Register the run in the in-memory registry so refreshed clients can
    # reconnect via GET /chat/sessions/{id}/stream and resume live streaming.
    state = _RunState()
    _active_runs[session_id] = state

    async def agent_worker():
        """Run the agent loop, persist DB rows, broadcast events to subscribers.

        Detached from any single HTTP request — keeps running even if every
        client disconnects, so DB state and the live broadcast both reach
        natural completion.
        """
        base_time = datetime.now(UTC)
        msg_index = 0
        collected_final_text = ""

        try:
            async for event in run_agent_stream(messages, session_id=session_id, model=request.model):
                name, data = _parse_sse(event)

                if name == "_persist_assistant":
                    blocks = data.get("blocks") or []
                    text_parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
                    text = "".join(text_parts)
                    async with get_session() as save_db:
                        save_db.add(ChatMessage(
                            session_id=session_id,
                            role="assistant",
                            content=text,
                            blocks=blocks,
                            model=active_model,
                            created_at=base_time + timedelta(microseconds=msg_index),
                        ))
                    msg_index += 1
                    collected_final_text = text
                    # The iteration is now in DB — drop its buffered events so
                    # late subscribers don't replay events for already-saved blocks.
                    await state.reset_iteration_buffer()
                    continue

                if name == "_persist_tool_results":
                    blocks = data.get("blocks") or []
                    async with get_session() as save_db:
                        save_db.add(ChatMessage(
                            session_id=session_id,
                            role="user",
                            content="",
                            blocks=blocks,
                            created_at=base_time + timedelta(microseconds=msg_index),
                        ))
                    msg_index += 1
                    continue

                await state.emit(event, name)

                if name == "done":
                    async with get_session() as save_db:
                        result = await save_db.execute(
                            select(ChatSession).where(ChatSession.id == session_id)
                        )
                        s = result.scalar_one_or_none()
                        if s:
                            s.updated_at = base_time + timedelta(microseconds=msg_index)

                    if collected_final_text.strip():
                        text_history = [
                            {"role": r.role, "content": r.content}
                            for r in rows
                            if r.content
                        ]
                        await maybe_trigger_review(session_id, text_history + [
                            {"role": "assistant", "content": collected_final_text},
                        ])
                        asyncio.create_task(maybe_synthesize_user_model())
        except Exception as e:
            await state.emit(
                f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n",
                "error",
            )
        finally:
            await state.finish()
            # Grace window for late reconnects to drain queued events,
            # then drop the registry entry so it doesn't leak.
            await asyncio.sleep(_RUN_CLEANUP_GRACE_SECONDS)
            _active_runs.pop(session_id, None)

    asyncio.create_task(agent_worker())

    async def stream_to_client():
        yield f"event: session\ndata: {json.dumps({'session_id': str(session_id)})}\n\n"
        q = await state.subscribe()
        try:
            while True:
                event = await q.get()
                if event is None:
                    break
                yield event
        finally:
            await state.unsubscribe(q)

    return StreamingResponse(
        stream_to_client(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/chat/sessions/{session_id}/stream")
async def stream_active_run(session_id: uuid.UUID) -> StreamingResponse:
    """Reconnect to an in-progress agent run for this session.

    Sends `event: no_active` and closes immediately if no run is live; otherwise
    replays the current iteration's buffered events and forwards new ones until
    the agent emits `done`.
    """
    state = _active_runs.get(session_id)

    async def stream():
        if state is None or state.done:
            yield "event: no_active\ndata: {}\n\n"
            return
        q = await state.subscribe()
        try:
            while True:
                event = await q.get()
                if event is None:
                    break
                yield event
        finally:
            await state.unsubscribe(q)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
