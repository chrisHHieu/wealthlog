"""Add verified_by_user + confidence to user_facts.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-04-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # verified_by_user lets retrieval rank facts the user explicitly confirmed
    # above ones the reviewer merely inferred — important for finance, where
    # confusing a guessed goal with a stated one would be misleading.
    op.add_column(
        "user_facts",
        sa.Column(
            "verified_by_user", sa.Boolean(),
            server_default=sa.false(), nullable=False,
        ),
    )
    # confidence is the reviewer's self-assessed certainty (1-10), distinct
    # from importance: a low-confidence guess can still be high-importance.
    # Used as the secondary tie-breaker in the retrieval order.
    op.add_column(
        "user_facts",
        sa.Column(
            "confidence", sa.Integer(),
            server_default="5", nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("user_facts", "confidence")
    op.drop_column("user_facts", "verified_by_user")
