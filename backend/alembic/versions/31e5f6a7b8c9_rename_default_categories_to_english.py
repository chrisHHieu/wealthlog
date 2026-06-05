"""Rename default categories to English.

Revision ID: 31e5f6a7b8c9
Revises: 30d4e5f6a7b8
Create Date: 2026-06-04

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "31e5f6a7b8c9"
down_revision: str | None = "30d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CATEGORY_RENAMES = {
    "L\u01b0\u01a1ng": "Salary",
    "Th\u01b0\u1edfng": "Bonus",
    "\u0110\u1ea7u t\u01b0 sinh l\u1eddi": "Investment returns",
    "Thu nh\u1eadp ph\u1ee5": "Side income",
    "Cho vay thu v\u1ec1": "Loan repayment",
    "\u0102n u\u1ed1ng": "Food & Dining",
    "Di chuy\u1ec3n": "Transportation",
    "S\u1ee9c kh\u1ecfe": "Healthcare",
    "Nh\u00e0 \u1edf": "Housing",
    "H\u00f3a \u0111\u01a1n & Ti\u1ec7n \u00edch": "Bills & Utilities",
    "Gia \u0111\u00ecnh": "Family",
    "Ph\u00ed ng\u00e2n h\u00e0ng": "Bank fees",
    "Mua s\u1eafm": "Shopping",
    "Gi\u1ea3i tr\u00ed": "Entertainment",
    "Gi\u00e1o d\u1ee5c": "Education",
    "L\u00e0m \u0111\u1eb9p": "Beauty",
    "Du l\u1ecbch": "Travel",
    "Kh\u00e1c": "Other",
    "C\u00f4ng vi\u1ec7c": "Work",
    "Gi\u1eb7t \u1ee7i / Sinh ho\u1ea1t": "Laundry / Living",
}


def _rename(mapping: dict[str, str]) -> None:
    categories = sa.table("categories", sa.column("name", sa.String()))
    connection = op.get_bind()
    for old_name, new_name in mapping.items():
        connection.execute(
            categories.update()
            .where(categories.c.name == old_name)
            .values(name=new_name)
        )


def upgrade() -> None:
    _rename(CATEGORY_RENAMES)


def downgrade() -> None:
    _rename({new_name: old_name for old_name, new_name in CATEGORY_RENAMES.items()})
