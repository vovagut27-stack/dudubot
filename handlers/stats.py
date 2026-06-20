"""
Статистика пользователя: /stats
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import DAILY_WORDS_FREE_PER_LANGUAGE, DAILY_WORDS_PREMIUM, FREE_MAX_LANGUAGES, SUPPORTED_LANGUAGES
from services.dispatch_time import format_notification_slot
from services.user_service import UserService
from services.word_service import WordService
from utils.menu_filters import menu_btn

logger = logging.getLogger(__name__)
router = Router(name="stats")


def _progress_bar(current: int, total: int, length: int = 10) -> str:
    """Рисует текстовый прогресс-бар."""
    if total <= 0:
        return "▱" * length
    filled = min(length, int(current / total * length))
    return "▰" * filled + "▱" * (length - filled)


@router.message(Command("stats"))
@router.message(menu_btn("btn_stats"))
async def cmd_stats(
    message: Message,
    session: AsyncSession,
    word_service: WordService,
) -> None:
    """Показывает статистику и геймификацию."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(message.from_user.id)

    if user is None or not user.onboarding_completed:
        await message.answer("Сначала пройдите онбординг: /start")
        return

    xp_needed = word_service.xp_for_level(user.xp_level)
    xp_in_level = user.points % xp_needed if xp_needed else user.points
    bar = _progress_bar(xp_in_level, xp_needed)

    langs = ", ".join(
        SUPPORTED_LANGUAGES.get(c, c) for c in user.language_list()
    )
    is_active = user_service.is_premium_active(user)
    premium = "⭐ Premium" if is_active else "🆓 Free"
    daily_limit = user_service.get_daily_word_limit(user)
    if is_active:
        langs_line = f"🌍 Языки: {langs} (безлимит)"
    else:
        active_count = len(user_service.effective_language_list(user))
        stored_count = len(user.language_list())
        if stored_count > active_count:
            langs_line = (
                f"🌍 Языки: {langs}\n"
                f"   ↳ активны <b>{active_count}</b> из {stored_count} "
                f"(Free — макс. {FREE_MAX_LANGUAGES}, Premium — безлимит)"
            )
        else:
            langs_line = f"🌍 Языки: {langs} (макс. {FREE_MAX_LANGUAGES} на Free)"
    until_line = ""
    if user.premium_until and is_active:
        until_line = f"\n📅 Premium до: <b>{user.premium_until.strftime('%d.%m.%Y %H:%M')} UTC</b>"

    text = (
        "📊 <b>Ваша статистика</b>\n\n"
        f"🏆 Уровень: <b>{user.xp_level}</b>\n"
        f"💎 Очки: <b>{user.points}</b>\n"
        f"{bar} {xp_in_level}/{xp_needed}\n\n"
        f"🔥 Streak: <b>{user.streak}</b> дн.\n"
        f"🌟 Лучший streak: <b>{user.best_streak}</b> дн.\n"
        f"📚 Выучено слов: <b>{user.words_learned}</b>\n\n"
        f"📬 Слов в день: <b>{daily_limit}</b> "
        f"(Free {DAILY_WORDS_FREE_PER_LANGUAGE}/язык · Premium {DAILY_WORDS_PREMIUM})\n"
        f"📊 CEFR: <b>{user.level}</b>\n"
        f"{langs_line}\n"
        f"🕐 Уведомления: <b>{format_notification_slot(user)}</b>\n"
        f"💳 Тариф: {premium}{until_line}"
    )

    await message.answer(text)
