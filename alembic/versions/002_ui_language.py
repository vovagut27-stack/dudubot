"""Add ui_language to users

Revision ID: 002_ui_language
Revises: 001_initial
Create Date: 2026-06-13
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_ui_language"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.add_column(
            "users",
            sa.Column("ui_language", sa.String(length=8), server_default="ru", nullable=False),
        )
        return

    rows = bind.execute(sa.text("PRAGMA table_info(users)")).fetchall()
    cols = {row[1] for row in rows}
    if "ui_language" not in cols:
        bind.execute(
            sa.text("ALTER TABLE users ADD COLUMN ui_language TEXT DEFAULT 'ru'")
        )


def downgrade() -> None:
    op.drop_column("users", "ui_language")
