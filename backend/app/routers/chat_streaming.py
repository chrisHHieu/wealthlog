"""Chat SSE stream orchestration."""

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta

from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.ai.agent import run_agent_stream
from app.ai.agent.message_history import db_rows_to_claude_messages, parse_sse
from app.ai.agent.run_registry import (
    RUN_CLEANUP_GRACE_SECONDS,
    RunState,
    active_runs,
)
from app.ai.memory.episodic import maybe_summarize_stale_sessions
from app.ai.memory.facts import maybe_trigger_review
from app.ai.memory.synthesis import maybe_synthesize_user_model
from app.database import get_session
from app.models.chat import ChatMessage, ChatSession
from app.routers.chat_persistence import (
    persist_assistant_row,
    persist_tool_result_row,
)
from app.schemas.ai.chat import ChatRequest


async def start_chat_stream(request: ChatRequest) -> StreamingResponse:
    """Stream AI agent response as SSE events, persisting chat history."""
    session_id = await _persist_user_message(request)
    asyncio.create_task(maybe_summarize_stale_sessions(exclude_session_id=session_id))

    from app.ai.model_registry import get_preferred_model

    active_model = request.model or await get_preferred_model()
    rows = await _load_message_rows(session_id)
    messages = db_rows_to_claude_messages(rows, active_model=active_model)

    state = RunState()
    active_runs[session_id] = state
    asyncio.create_task(_agent_worker(
        request=request,
        session_id=session_id,
        active_model=active_model,
        messages=messages,
        rows=rows,
        state=state,
    ))

    async def stream_to_client():
        yield f"event: session\ndata: {json.dumps({'session_id': str(session_id)})}\n\n"
        queue = await state.subscribe()
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
        finally:
            await state.unsubscribe(queue)

    return _sse_response(stream_to_client())


async def reconnect_active_run(session_id: uuid.UUID) -> StreamingResponse:
    """Reconnect to an in-progress agent run for this session."""
    state = active_runs.get(session_id)

    async def stream():
        if state is None or state.done:
            yield "event: no_active\ndata: {}\n\n"
            return
        queue = await state.subscribe()
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
        finally:
            await state.unsubscribe(queue)

    return _sse_response(stream())


async def _persist_user_message(request: ChatRequest) -> uuid.UUID:
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

        return session_id


async def _load_message_rows(session_id: uuid.UUID) -> list[ChatMessage]:
    async with get_session() as load_db:
        result = await load_db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at, ChatMessage.id)
        )
        return list(result.scalars().all())


async def _agent_worker(
    request: ChatRequest,
    session_id: uuid.UUID,
    active_model: str,
    messages: list[dict],
    rows: list[ChatMessage],
    state: RunState,
) -> None:
    base_time = datetime.now(UTC)
    msg_index = 0
    collected_final_text = ""

    try:
        async for event in run_agent_stream(
            messages,
            session_id=session_id,
            model=request.model,
        ):
            name, data = parse_sse(event)

            if name == "_persist_assistant":
                blocks = data.get("blocks") or []
                text = await persist_assistant_row(
                    session_id=session_id,
                    blocks=blocks,
                    model=active_model,
                    created_at=base_time + timedelta(microseconds=msg_index),
                )
                msg_index += 1
                collected_final_text = text
                await state.reset_iteration_buffer()
                continue

            if name == "_persist_tool_results":
                blocks = data.get("blocks") or []
                await persist_tool_result_row(
                    session_id=session_id,
                    blocks=blocks,
                    base_time=base_time,
                    msg_index=msg_index,
                )
                msg_index += 1
                continue

            await state.emit(event, name)

            if name == "done":
                await _mark_session_done(session_id, base_time, msg_index)
                if collected_final_text.strip():
                    text_history = [
                        {"role": row.role, "content": row.content}
                        for row in rows
                        if row.content
                    ]
                    await maybe_trigger_review(session_id, text_history + [
                        {"role": "assistant", "content": collected_final_text},
                    ])
                    asyncio.create_task(maybe_synthesize_user_model())
    except Exception as exc:
        await state.emit(
            f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n",
            "error",
        )
    finally:
        await state.finish()
        await asyncio.sleep(RUN_CLEANUP_GRACE_SECONDS)
        active_runs.pop(session_id, None)


async def _mark_session_done(
    session_id: uuid.UUID,
    base_time: datetime,
    msg_index: int,
) -> None:
    async with get_session() as save_db:
        result = await save_db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if session:
            session.updated_at = base_time + timedelta(microseconds=msg_index)


def _sse_response(stream) -> StreamingResponse:
    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
