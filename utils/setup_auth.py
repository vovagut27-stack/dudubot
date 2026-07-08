"""Коды активации Premium в боте."""

from __future__ import annotations

import os


def _valid_activation_codes() -> set[str]:
    """Коды для /premium и /test_premium."""
    premium = os.getenv("PREMIUM_ACTIVATION_CODE", "").strip()
    return {premium} if premium else set()


def _valid_premium_codes() -> set[str]:
    """Коды для пользовательской активации Premium."""
    return _valid_activation_codes()


def check_activation_code(token: str | None) -> bool:
    """True для бот-кода активации Premium."""
    if not token:
        return False
    return token.strip() in _valid_activation_codes()


def check_premium_activation_code(token: str | None) -> bool:
    """True для пользовательской активации Premium через /premium."""
    if not token:
        return False
    return token.strip() in _valid_premium_codes()


def looks_like_activation_code(text: str | None) -> bool:
    """Похоже на попытку ввести код (чтобы ответить, а не молчать)."""
    if not text:
        return False
    t = text.strip()
    if t.startswith("/"):
        return False
    if t.startswith("dudu_") or t.startswith("appss_"):
        return True
    return len(t) >= 16 and t.replace("_", "").isalnum()
