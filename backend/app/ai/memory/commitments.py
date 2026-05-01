"""Commitment tracking — things the user explicitly said they would do."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update

from app.database import get_session
from app.logging_config import get_logger
from app.models.user_commitment import UserCommitment

logger = get_logger(__name__)

_VALID_STATUSES = ("pending", "done", "abandoned")


async def save_commitment(
    text: str,
    source_session_id: uuid.UUID | None = None,
    due_by: datetime | None = None,
) -> None:
    """Persist a new pending commitment extracted from a session summary."""
    stripped = text.strip()
    if not stripped:
        return
    async with get_session() as db:
        db.add(UserCommitment(
            text=stripped,
            source_session_id=source_session_id,
            due_by=due_by,
            status="pending",
        ))


async def get_pending_commitments(
    max_age_days: int = 30,
    limit: int = 8,
) -> list[UserCommitment]:
    """Return pending commitments not older than ``max_age_days``, oldest first.

    Oldest-first ordering surfaces the most overdue items at the top of the
    prompt block so the agent sees them before newer ones.
    """
    cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
    async with get_session() as db:
        return list(
            (
                await db.execute(
                    select(UserCommitment)
                    .where(
                        UserCommitment.status == "pending",
                        UserCommitment.created_at >= cutoff,
                    )
                    .order_by(UserCommitment.created_at.asc())
                    .limit(limit)
                )
            ).scalars().all()
        )


async def update_commitment_status(
    commitment_id: uuid.UUID,
    status: str,
) -> bool:
    """Mark a commitment as 'done' or 'abandoned'. Returns True if found."""
    if status not in _VALID_STATUSES:
        return False
    async with get_session() as db:
        result = await db.execute(
            update(UserCommitment)
            .where(UserCommitment.id == commitment_id)
            .values(status=status, updated_at=datetime.now(UTC))
            .returning(UserCommitment.id)
        )
        return result.scalar_one_or_none() is not None


async def build_commitments_prompt(max_age_days: int = 30) -> str:
    """Render pending commitments as a dynamic system-prompt block.

    The agent uses this block to follow up naturally — not to interrogate
    the user, but to acknowledge commitments when the topic arises.
    """
    pending = await get_pending_commitments(max_age_days=max_age_days)
    if not pending:
        return ""

    now = datetime.now(UTC)
    lines = ["[Things the user said they would do]"]
    for c in pending:
        created = c.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        age_days = (now - created).days
        age_str = "today" if age_days == 0 else f"{age_days}d ago"
        lines.append(f'- "{c.text}" (committed {age_str})')
    lines.append(
        "[Follow up naturally when relevant — don't interrogate, "
        "just acknowledge if the topic comes up]"
    )
    return "\n".join(lines)
