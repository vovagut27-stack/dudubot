"""Проверка SETUP_SECRET (тест Premium, migrate API)."""

from __future__ import annotations

import os


def check_setup_secret(token: str | None) -> bool:
    """True, если token совпадает с SETUP_SECRET из окружения."""
    if not token:
        return False
    expected = os.getenv("SETUP_SECRET", "")
    return bool(expected) and token.strip() == expected
