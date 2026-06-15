"""Ручная (тестовая) выдача Premium без оплаты Stars."""

from __future__ import annotations

from bootstrap import ensure_database
from config import PREMIUM_TEST_DAYS, get_settings
from database import session_scope
from services.user_service import UserService


async def grant_test_premium_to(telegram_id: int, *, days: int | None = None) -> dict:
    """Выдаёт Premium пользователю по Telegram ID."""
    settings = get_settings()
    await ensure_database(settings)

    grant_days = days if days and days > 0 else PREMIUM_TEST_DAYS

    async with session_scope() as session:
        user_service = UserService(session)
        user = await user_service.get_by_telegram_id(telegram_id)
        if user is None:
            user = await user_service.get_or_create(telegram_id=telegram_id)
        until = user_service.grant_test_premium(user, days=grant_days)

    return {
        "ok": True,
        "telegram_id": telegram_id,
        "premium_until": until.isoformat(),
        "days_granted": grant_days,
        "is_premium": True,
    }
