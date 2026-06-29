"""Add preview column to pending_actions.

Revision ID: 86d0e1f2a3b4
Revises: 75c9d0e1f2a3
Create Date: 2026-06-23
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "86d0e1f2a3b4"
down_revision: str | None = "75c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pending_actions",
        sa.Column("preview", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pending_actions", "preview")
