"""Коды активации Premium (бот и API)."""

from __future__ import annotations

import os


def _valid_admin_codes() -> set[str]:
    """Коды для /test_premium и админской активации."""
    codes: set[str] = set()
    setup = os.getenv("SETUP_SECRET", "").strip()
    premium = os.getenv("PREMIUM_ACTIVATION_CODE", "").strip()
    if setup:
        codes.add(setup)
    if premium:
        codes.add(premium)
    return codes


def _valid_premium_codes() -> set[str]:
    """Коды для /premium (только PREMIUM_ACTIVATION_CODE, не SETUP_SECRET)."""
    premium = os.getenv("PREMIUM_ACTIVATION_CODE", "").strip()
    return {premium} if premium else set()


def check_activation_code(token: str | None) -> bool:
    """True для админских кодов (SETUP_SECRET или PREMIUM_ACTIVATION_CODE)."""
    if not token:
        return False
    return token.strip() in _valid_admin_codes()


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
