"""Enable pg_trgm and add a GIN index on user_facts.fact for fuzzy dedup.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-04-27

"""

from collections.abc import Sequence

from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Trigram-backed GIN index lets save_user_fact() detect near-duplicates
    # ("save 50M for car" vs "saving 50M to buy a car") via similarity() instead
    # of strict equality, without scanning the whole table on every insert.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_facts_fact_trgm "
        "ON user_facts USING gin (fact gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_user_facts_fact_trgm")
    # Intentionally NOT dropping pg_trgm — other tables/indexes may depend on it.
