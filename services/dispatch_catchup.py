"""Догоняющая рассылка: если cron не сработал, отправить слова после времени пользователя."""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import Settings
from database import session_scope
from handlers.daily import send_daily_word_to_user
from services.dispatch_time import is_past_notification_today, user_local_now
from services.user_service import UserService
from services.word_service import WordService

logger = logging.getLogger(__name__)


def _telegram_user_id(event: TelegramObject) -> int | None:
    if isinstance(event, Message) and event.from_user:
        return event.from_user.id
    if isinstance(event, CallbackQuery) and event.from_user:
        return event.from_user.id
    return None


async def try_catchup_daily_words(
    event: TelegramObject,
    bot: Bot,
    word_service: WordService,
    settings: Settings,
) -> bool:
    """
    Отправляет слова дня, если время рассылки уже наступило, а cron не доставил.

    Returns:
        True если слова отправлены.
    """
    telegram_id = _telegram_user_id(event)
    if telegram_id is None:
        return False

    async with session_scope() as session:
        user_service = UserService(session)
        user = await user_service.get_by_telegram_id(telegram_id)
        if user is None or not user.onboarding_completed:
            return False

        now = user_local_now(user, settings.timezone)
        if not is_past_notification_today(user, now):
            return False

        today_logs = await user_service.get_today_words(user, now.date())
        limit = user_service.get_daily_word_limit(user)
        if len(today_logs) >= limit:
            return False

        logger.info(
            "Catch-up рассылка user=%s slot=%s local=%s",
            user.telegram_id,
            user.notification_time,
            now.strftime("%Y-%m-%d %H:%M"),
        )
        delivered = await send_daily_word_to_user(
            bot=bot,
            user=user,
            session=session,
            word_service=word_service,
            user_service=user_service,
            target_date=now.date(),
            default_tz=settings.timezone,
            notify_if_complete=False,
        )
        return delivered > 0
