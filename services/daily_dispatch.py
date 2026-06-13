"""
Ежедневная рассылка слов — используется APScheduler (локально) и Vercel Cron.
"""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import Bot

from config import Settings
from database import async_session_factory, session_scope, use_sync_sessions
from handlers.daily import send_daily_word_to_user
from services.user_service import UserService
from services.word_service import WordService

logger = logging.getLogger(__name__)


async def run_daily_dispatch(
    bot: Bot,
    settings: Settings,
    word_service: WordService,
) -> dict[str, int]:
    """
    Отправляет слово дня пользователям, у которых наступило время уведомления.

    Returns:
        Статистика: {"users": N, "sent": M}
    """
    if async_session_factory is None and not use_sync_sessions:
        logger.warning("Session factory не инициализирована")
        return {"users": 0, "sent": 0}

    tz = ZoneInfo(settings.timezone)
    now = datetime.now(tz)
    hour, minute = now.hour, now.minute
    sent = 0
    users: list = []

    async with session_scope() as session:
        user_service = UserService(session)
        users = await user_service.get_users_for_notification(hour, minute)

        for user in users:
            try:
                await send_daily_word_to_user(
                    bot=bot,
                    user=user,
                    session=session,
                    word_service=word_service,
                    user_service=user_service,
                    target_date=now.date(),
                )
                sent += 1
            except Exception:
                logger.exception("Ошибка рассылки user_id=%s", user.telegram_id)

    if users:
        logger.info(
            "Рассылка: %d пользователей, отправлено %d в %02d:%02d",
            len(users),
            sent,
            hour,
            minute,
        )

    return {"users": len(users), "sent": sent}
