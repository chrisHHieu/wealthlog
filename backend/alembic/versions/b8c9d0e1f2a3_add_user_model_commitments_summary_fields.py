"""Add user_models, user_commitments, and enrich session_summaries.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-04-30

Changes:
- New table: user_models (versioned Sonnet-synthesized user profiles)
- New table: user_commitments (things the user said they'd do)
- session_summaries: add commitments (JSONB), pushback (text), open_questions (JSONB)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_models",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("session_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_commitments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source_session_id", sa.UUID(), nullable=True),
        sa.Column("due_by", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), server_default="'pending'", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_session_id"],
            ["chat_sessions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_user_commitments_status",
        "user_commitments",
        ["status", "created_at"],
    )

    # Nullable JSONB/JSON columns on session_summaries for backward compatibility.
    # Existing rows remain valid — new fields appear only on summaries written
    # after this migration.
    op.add_column(
        "session_summaries",
        sa.Column(
            "commitments",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "session_summaries",
        sa.Column("pushback", sa.Text(), nullable=True),
    )
    op.add_column(
        "session_summaries",
        sa.Column(
            "open_questions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("session_summaries", "open_questions")
    op.drop_column("session_summaries", "pushback")
    op.drop_column("session_summaries", "commitments")
    op.drop_index("ix_user_commitments_status", table_name="user_commitments")
    op.drop_table("user_commitments")
    op.drop_table("user_models")
