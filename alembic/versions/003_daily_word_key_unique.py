"""Fix daily_word_logs unique constraint to word_key

Revision ID: 003_daily_word_key
Revises: 002_ui_language
Create Date: 2026-06-13
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_daily_word_key"
down_revision: Union[str, None] = "002_ui_language"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.drop_constraint("uq_daily_word", "daily_word_logs", type_="unique")
        op.create_unique_constraint(
            "uq_daily_word", "daily_word_logs", ["user_id", "sent_date", "word_key"]
        )
        return

    row = bind.execute(
        sa.text(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='daily_word_logs'"
        )
    ).fetchone()
    if not row or not row[0]:
        return

    unique_part = row[0].upper().split("UNIQUE")[-1]
    if "WORD_KEY" in unique_part or "LANGUAGE" not in unique_part:
        return

    bind.execute(
        sa.text(
            """
            CREATE TABLE daily_word_logs_new (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                word_key VARCHAR(128) NOT NULL,
                language VARCHAR(8) NOT NULL,
                sent_date DATE NOT NULL,
                message_id BIGINT,
                FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE (user_id, sent_date, word_key)
            )
            """
        )
    )
    bind.execute(
        sa.text(
            """
            INSERT INTO daily_word_logs_new
                (id, user_id, word_key, language, sent_date, message_id)
            SELECT id, user_id, word_key, language, sent_date, message_id
            FROM daily_word_logs
            """
        )
    )
    bind.execute(sa.text("DROP TABLE daily_word_logs"))
    bind.execute(sa.text("ALTER TABLE daily_word_logs_new RENAME TO daily_word_logs"))


def downgrade() -> None:
    pass
