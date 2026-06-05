"""Add chat message session-role-created index.

Revision ID: 30d4e5f6a7b8
Revises: 20c3d4e5f6a7
Create Date: 2026-06-04

"""

from collections.abc import Sequence

from alembic import op

revision: str = "30d4e5f6a7b8"
down_revision: str | None = "20c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_chat_messages_session_role_created",
        "chat_messages",
        ["session_id", "role", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_chat_messages_session_role_created",
        table_name="chat_messages",
    )
