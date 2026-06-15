"""
Ежедневная рассылка слов — APScheduler (локально) и Vercel Cron.
"""

from __future__ import annotations

import logging

from aiogram import Bot

from config import Settings
from database import async_session_factory, session_scope, use_sync_sessions
from handlers.daily import send_daily_word_to_user
from services.dispatch_time import is_notification_hour, user_local_now
from services.user_service import UserService
from services.word_service import WordService

logger = logging.getLogger(__name__)


async def run_daily_dispatch(
    bot: Bot,
    settings: Settings,
    word_service: WordService,
) -> dict[str, int]:
    """
    Отправляет слова пользователям, у которых наступил час уведомления.

    Слоты: 07:00, 08:00, 09:00, 12:00, 18:00, 20:00, 21:00 (локальное время).
    Cron вызывается каждый час — попадание в слот по часу, не по минуте.

    Returns:
        Статистика: {"users": N, "sent": M, "skipped": K}
    """
    if async_session_factory is None and not use_sync_sessions:
        logger.warning("Session factory не инициализирована")
        return {"users": 0, "sent": 0, "skipped": 0}

    sent = 0
    matched = 0
    skipped = 0

    async with session_scope() as session:
        user_service = UserService(session)
        users = await user_service.get_onboarded_users()

    for user in users:
        try:
            now = user_local_now(user, settings.timezone)
            if not is_notification_hour(user, now):
                continue

            async with session_scope() as session:
                user_service = UserService(session)
                db_user = await user_service.get_by_telegram_id(user.telegram_id)
                if db_user is None:
                    continue

                today_logs = await user_service.get_today_words(db_user, now.date())
                limit = user_service.get_daily_word_limit(db_user)
                if len(today_logs) >= limit:
                    skipped += 1
                    continue

                matched += 1
                logger.info(
                    "Рассылка user=%s slot=%s local=%s",
                    db_user.telegram_id,
                    db_user.notification_time.strftime("%H:%M"),
                    now.strftime("%Y-%m-%d %H:%M"),
                )
                delivered = await send_daily_word_to_user(
                    bot=bot,
                    user=db_user,
                    session=session,
                    word_service=word_service,
                    user_service=user_service,
                    target_date=now.date(),
                    default_tz=settings.timezone,
                    notify_if_complete=False,
                )
            if delivered > 0:
                sent += 1
        except Exception:
            logger.exception("Ошибка рассылки user_id=%s", user.telegram_id)

    if matched or skipped:
        logger.info(
            "Рассылка: matched=%d sent=%d skipped(already)=%d",
            matched,
            sent,
            skipped,
        )

    return {"users": matched, "sent": sent, "skipped": skipped}
