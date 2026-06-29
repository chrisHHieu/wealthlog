"""Drop weekly_digests table (digest feature removed).

Revision ID: 75c9d0e1f2a3
Revises: 64b8c9d0e1f2
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "75c9d0e1f2a3"
down_revision: str | None = "64b8c9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_weekly_digests_created_at", table_name="weekly_digests")
    op.drop_table("weekly_digests")


def downgrade() -> None:
    op.create_table(
        "weekly_digests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("generated_for_month", sa.String(7), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_weekly_digests_created_at",
        "weekly_digests",
        ["created_at"],
    )
