"""Merge two migration heads into one.

Branch A (main chain) ended at 10b2c3d4e5f6 (add model to chat_messages).
Branch B ended at d0e1f2a3b4c5 (add fact topics).

Revision ID: 20c3d4e5f6a7
Revises: 10b2c3d4e5f6, d0e1f2a3b4c5
Create Date: 2026-05-01

"""

from collections.abc import Sequence

from alembic import op

revision: str = "20c3d4e5f6a7"
down_revision: tuple[str, str] = ("10b2c3d4e5f6", "d0e1f2a3b4c5")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
