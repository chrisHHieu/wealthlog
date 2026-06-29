"""Add bi-temporal supersession columns to user_facts.

Revision ID: 64b8c9d0e1f2
Revises: 53a7b8c9d0e1
Create Date: 2026-06-22
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "64b8c9d0e1f2"
down_revision: str | None = "53a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_facts",
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "user_facts",
        sa.Column("supersedes_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_user_facts_supersedes_id",
        "user_facts",
        "user_facts",
        ["supersedes_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # Active-fact retrieval filters on `superseded_at IS NULL`; index the live set.
    op.create_index(
        "ix_user_facts_superseded_at",
        "user_facts",
        ["superseded_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_facts_superseded_at", table_name="user_facts")
    op.drop_constraint("fk_user_facts_supersedes_id", "user_facts", type_="foreignkey")
    op.drop_column("user_facts", "supersedes_id")
    op.drop_column("user_facts", "superseded_at")
