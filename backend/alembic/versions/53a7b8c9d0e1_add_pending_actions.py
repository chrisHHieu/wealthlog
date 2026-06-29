"""Add pending_actions table.

Revision ID: 53a7b8c9d0e1
Revises: 42f6a7b8c9d0
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "53a7b8c9d0e1"
down_revision: str | None = "42f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pending_actions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=True),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("arguments", JSONB(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["session_id"], ["chat_sessions.id"], ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pending_actions_session_status",
        "pending_actions",
        ["session_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_pending_actions_session_status", table_name="pending_actions")
    op.drop_table("pending_actions")
