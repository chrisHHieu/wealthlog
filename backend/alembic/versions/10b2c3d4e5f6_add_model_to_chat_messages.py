"""Add model column to chat_messages.

Revision ID: 10b2c3d4e5f6
Revises: f6a7b8c9d0e1
Create Date: 2026-05-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "10b2c3d4e5f6"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "chat_messages",
        sa.Column("model", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("chat_messages", "model")
