"""Add nullable outcome column to session_summaries.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-04-27

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # outcome captures the *result* of the session — what was decided or
    # accomplished — separate from the narrative summary. Lets the prompt
    # block render a one-line punch ("đã lập budget tháng 4") instead of
    # always showing the 2-4 sentence summary, freeing tokens at retrieval.
    # Nullable so existing rows render unchanged until the next summarize pass.
    op.add_column(
        "session_summaries",
        sa.Column("outcome", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("session_summaries", "outcome")
