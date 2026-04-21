"""Add importance, access_count, last_accessed_at to user_facts.

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_facts",
        sa.Column("importance", sa.Integer(), server_default="5", nullable=False),
    )
    op.add_column(
        "user_facts",
        sa.Column("access_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "user_facts",
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_facts", "last_accessed_at")
    op.drop_column("user_facts", "access_count")
    op.drop_column("user_facts", "importance")
