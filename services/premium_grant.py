"""Ручная (тестовая) выдача Premium без оплаты Stars."""

from __future__ import annotations

import os

from sqlalchemy import select

from config import PREMIUM_TEST_DAYS, get_settings
from database import ensure_database_ready, session_scope
from models.models import User
from services.user_service import UserService


def _normalize_username(username: str) -> str:
    return username.strip().lstrip("@")


async def resolve_telegram_id_by_username(username: str) -> int | None:
    """Ищет Telegram ID по @username в БД или через Bot API getChat."""
    name = _normalize_username(username)
    if not name:
        return None

    settings = get_settings()
    await ensure_database_ready(settings)

    async with session_scope() as session:
        result = await session.execute(
            select(User.telegram_id).where(User.username.ilike(name))
        )
        telegram_id = result.scalar_one_or_none()
        if telegram_id is not None:
            return int(telegram_id)

    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        return None

    from aiogram import Bot

    bot = Bot(token=token)
    try:
        chat = await bot.get_chat(f"@{name}")
        return int(chat.id)
    except Exception:
        return None
    finally:
        await bot.session.close()


async def grant_test_premium_to(telegram_id: int, *, days: int | None = None) -> dict:
    """Выдаёт Premium пользователю по Telegram ID."""
    settings = get_settings()
    await ensure_database_ready(settings)

    grant_days = days if days and days > 0 else PREMIUM_TEST_DAYS

    async with session_scope() as session:
        user_service = UserService(session)
        user = await user_service.get_by_telegram_id(telegram_id)
        if user is None:
            user = await user_service.get_or_create(telegram_id=telegram_id)
        until = user_service.grant_test_premium(user, days=grant_days)
        await session.flush()
        verified = user_service.is_premium_active(user)

    return {
        "ok": True,
        "telegram_id": telegram_id,
        "premium_until": until.isoformat(),
        "days_granted": grant_days,
        "is_premium_db": bool(user.is_premium),
        "verified_active": verified,
    }


async def grant_test_premium_by_username(username: str, *, days: int | None = None) -> dict:
    """Выдаёт Premium по @username (БД или Telegram getChat)."""
    name = _normalize_username(username)
    telegram_id = await resolve_telegram_id_by_username(name)
    if telegram_id is None:
        return {
            "ok": False,
            "username": name,
            "error": "Пользователь не найден. Нужен /start в боте или публичный @username.",
        }

    result = await grant_test_premium_to(telegram_id, days=days)
    result["username"] = name
    return result


async def get_premium_status(telegram_id: int) -> dict:
    """Читает статус Premium из БД (диагностика)."""
    settings = get_settings()
    await ensure_database_ready(settings)

    async with session_scope() as session:
        user_service = UserService(session)
        user = await user_service.get_by_telegram_id(telegram_id)
        if user is None:
            return {
                "ok": True,
                "found": False,
                "telegram_id": telegram_id,
                "verified_active": False,
            }
        active = user_service.is_premium_active(user)
        return {
            "ok": True,
            "found": True,
            "telegram_id": telegram_id,
            "is_premium_db": bool(user.is_premium),
            "premium_until": user.premium_until.isoformat() if user.premium_until else None,
            "verified_active": active,
            "daily_word_limit": user_service.get_daily_word_limit(user),
        }
