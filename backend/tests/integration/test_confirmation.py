"""Write-action confirmation gate: defer, execute, reject + endpoints."""

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent import confirmation
from app.models.pending_action import PendingAction


def _patch_session(db: AsyncSession):
    @asynccontextmanager
    async def _mock():
        yield db

    return patch("app.ai.agent.confirmation.get_session", _mock)


def test_requires_confirmation_flags_writes_not_reads():
    assert confirmation.requires_confirmation("create_transaction")
    assert confirmation.requires_confirmation("delete_transaction")
    assert confirmation.requires_confirmation("update_transaction")
    assert confirmation.requires_confirmation("create_multiple_transactions")
    assert not confirmation.requires_confirmation("list_transactions")
    assert not confirmation.requires_confirmation("get_report")


async def test_defer_action_persists_pending_and_returns_message(db: AsyncSession):
    with _patch_session(db):
        action_id, message, _ = await confirmation.defer_action(
            None, "create_transaction", {"amount": 100, "type": "expense"},
        )

    assert action_id in message
    assert "NOT EXECUTED" in message
    row = (await db.execute(select(PendingAction))).scalar_one()
    assert str(row.id) == action_id
    assert row.status == "pending"
    assert row.tool_name == "create_transaction"
    assert row.arguments["amount"] == 100


async def test_execute_pending_runs_tool_and_marks_executed(db: AsyncSession):
    with _patch_session(db):
        action_id, _, _ = await confirmation.defer_action(
            None, "create_transaction", {"amount": 50},
        )
        with patch(
            "app.ai.agent.confirmation.execute_tool",
            AsyncMock(return_value=("Created transaction.", False)),
        ) as exec_mock:
            text, is_error = await confirmation.execute_pending(uuid.UUID(action_id))

    assert is_error is False
    assert text == "Created transaction."
    exec_mock.assert_awaited_once_with("create_transaction", {"amount": 50})
    row = await db.get(PendingAction, uuid.UUID(action_id))
    assert row.status == "executed"
    assert row.result == "Created transaction."
    assert row.resolved_at is not None


async def test_execute_pending_failure_marks_failed(db: AsyncSession):
    with _patch_session(db):
        action_id, _, _ = await confirmation.defer_action(None, "delete_transaction", {"id": "x"})
        with patch(
            "app.ai.agent.confirmation.execute_tool",
            AsyncMock(return_value=("Tool error", True)),
        ):
            _, is_error = await confirmation.execute_pending(uuid.UUID(action_id))

    assert is_error is True
    row = await db.get(PendingAction, uuid.UUID(action_id))
    assert row.status == "failed"


async def test_execute_pending_missing_raises_lookup(db: AsyncSession):
    with _patch_session(db), pytest.raises(LookupError):
        await confirmation.execute_pending(uuid.uuid4())


async def test_execute_pending_already_resolved_raises_value(db: AsyncSession):
    with _patch_session(db):
        action_id, _, _ = await confirmation.defer_action(None, "update_transaction", {})
        with patch(
            "app.ai.agent.confirmation.execute_tool",
            AsyncMock(return_value=("ok", False)),
        ):
            await confirmation.execute_pending(uuid.UUID(action_id))
        with pytest.raises(ValueError, match="already executed"):
            await confirmation.execute_pending(uuid.UUID(action_id))


async def test_reject_pending_marks_rejected_without_executing(db: AsyncSession):
    with _patch_session(db):
        action_id, _, _ = await confirmation.defer_action(None, "create_transaction", {})
        await confirmation.reject_pending(uuid.UUID(action_id))

    row = await db.get(PendingAction, uuid.UUID(action_id))
    assert row.status == "rejected"
    assert row.resolved_at is not None


# ── Resolution feedback: confirm/reject rewrites the deferred tool_result ─────


async def _seed_pending_with_history(db: AsyncSession, tool_name: str):
    """A session + the deferred tool_result row + a pending action, all linked."""
    from app.models.chat import ChatMessage, ChatSession

    session = ChatSession(title="t")
    db.add(session)
    await db.flush()
    action = PendingAction(
        session_id=session.id, tool_name=tool_name, arguments={}, status="pending",
    )
    db.add(action)
    await db.flush()
    row = ChatMessage(session_id=session.id, role="user", content="", blocks=[
        {"type": "tool_result", "tool_use_id": "t1",
         "content": f"⏸ NOT EXECUTED — queued (action_id={action.id})"},
    ])
    db.add(row)
    await db.flush()
    return action.id, row


async def test_confirm_rewrites_tool_result_with_outcome(db: AsyncSession):
    action_id, row = await _seed_pending_with_history(db, "update_transaction")
    with _patch_session(db), patch(
        "app.ai.agent.confirmation.execute_tool",
        AsyncMock(return_value=("Updated 1 transaction.", False)),
    ):
        await confirmation.execute_pending(action_id)

    content = row.blocks[0]["content"]
    assert "User CONFIRMED" in content
    assert "Updated 1 transaction." in content
    assert "NOT EXECUTED" not in content


async def test_reject_rewrites_tool_result_with_outcome(db: AsyncSession):
    action_id, row = await _seed_pending_with_history(db, "delete_transaction")
    with _patch_session(db):
        await confirmation.reject_pending(action_id)

    content = row.blocks[0]["content"]
    assert "User REJECTED" in content
    assert "no changes" in content.lower()


async def test_resolution_is_noop_when_block_absent(db: AsyncSession):
    """If the tool_result was compacted away, resolving must not crash."""
    with _patch_session(db):
        action_id, _, _ = await confirmation.defer_action(None, "create_transaction", {})
        await confirmation.reject_pending(uuid.UUID(action_id))  # no history row exists

    assert (await db.get(PendingAction, uuid.UUID(action_id))).status == "rejected"


# ── Endpoint contract (routing + status codes) ───────────────────────────────


async def test_confirm_endpoint_executes(client):
    aid = uuid.uuid4()
    with patch(
        "app.routers.chat.execute_pending",
        AsyncMock(return_value=("Created.", False)),
    ):
        resp = await client.post(f"/api/chat/actions/{aid}/confirm")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "result": "Created."}


async def test_confirm_endpoint_missing_is_404(client):
    aid = uuid.uuid4()
    with patch(
        "app.routers.chat.execute_pending",
        AsyncMock(side_effect=LookupError("Pending action")),
    ):
        resp = await client.post(f"/api/chat/actions/{aid}/confirm")
    assert resp.status_code == 404


async def test_confirm_endpoint_resolved_is_409(client):
    aid = uuid.uuid4()
    with patch(
        "app.routers.chat.execute_pending",
        AsyncMock(side_effect=ValueError("Action already executed")),
    ):
        resp = await client.post(f"/api/chat/actions/{aid}/confirm")
    assert resp.status_code == 409


async def test_reject_endpoint_ok(client):
    aid = uuid.uuid4()
    with patch(
        "app.routers.chat.reject_pending",
        AsyncMock(return_value=None),
    ):
        resp = await client.post(f"/api/chat/actions/{aid}/reject")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
