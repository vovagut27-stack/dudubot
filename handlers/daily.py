"""
Ежедневное слово: /today, inline-действия, рассылка.
"""

from __future__ import annotations

import logging
from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import SUPPORTED_LANGUAGES
from models.models import User, WordStatus
from services.user_service import UserService
from services.word_service import WordEntry, WordService
from utils.keyboards import word_actions_keyboard

logger = logging.getLogger(__name__)
router = Router(name="daily")


async def send_daily_word_to_user(
    bot,
    user: User,
    session: AsyncSession,
    word_service: WordService,
    user_service: UserService,
    target_date: date | None = None,
) -> None:
    """
    Отправляет слово дня по всем языкам пользователя.

    Используется и в /today, и в планировщике.
    """
    target_date = target_date or date.today()
    languages = user.language_list() or ["en"]

    for lang in languages:
        word = word_service.pick_daily_word(
            language=lang,
            level=user.level,
            target_date=target_date,
            user_id=user.telegram_id,
        )
        if word is None:
            logger.warning("Нет слов для lang=%s level=%s", lang, user.level)
            continue

        progress = await user_service.get_word_progress(user.id, word.key)
        in_dict = progress is not None and progress.status in (
            WordStatus.FAVORITE.value,
            WordStatus.LEARNED.value,
        )

        lang_label = SUPPORTED_LANGUAGES.get(lang, lang)
        header = f"📬 Слово дня · {lang_label}"
        text = word_service.format_word_message(word, header=header)

        msg = await bot.send_message(
            chat_id=user.telegram_id,
            text=text,
            reply_markup=word_actions_keyboard(word.key, in_dictionary=in_dict),
        )
        await user_service.log_daily_word(
            user=user,
            word_key=word.key,
            language=lang,
            sent_date=target_date,
            message_id=msg.message_id,
        )


async def _send_today_words(
    message: Message,
    session: AsyncSession,
    word_service: WordService,
) -> None:
    """Общая логика команды /today."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(message.from_user.id)

    if user is None or not user.onboarding_completed:
        await message.answer("Сначала пройдите онбординг: /start")
        return

    await send_daily_word_to_user(
        bot=message.bot,
        user=user,
        session=session,
        word_service=word_service,
        user_service=user_service,
    )


@router.message(Command("today"))
@router.message(F.text == "📚 Слово дня")
async def cmd_today(message: Message, session: AsyncSession, word_service: WordService) -> None:
    """Получить слово дня вручную."""
    try:
        await _send_today_words(message, session, word_service)
    except Exception:
        logger.exception("Ошибка /today для user=%s", message.from_user.id)
        await message.answer("😔 Не удалось получить слово. Попробуйте позже.")


@router.callback_query(F.data.startswith("word:learned:"))
async def word_learned(
    callback: CallbackQuery,
    session: AsyncSession,
    word_service: WordService,
) -> None:
    """Пользователь отметил слово как выученное."""
    word_key = callback.data.split(":")[-1]
    word = word_service.get_by_key(word_key)
    if word is None:
        await callback.answer("Слово не найдено", show_alert=True)
        return

    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    _, msg = await user_service.mark_word(
        user, word_key, WordStatus.LEARNED, word_service=word_service
    )
    await callback.answer(msg[:200], show_alert=True)


@router.callback_query(F.data.startswith("word:unknown:"))
async def word_unknown(
    callback: CallbackQuery,
    session: AsyncSession,
    word_service: WordService,
) -> None:
    """Пользователь не знает слово."""
    word_key = callback.data.split(":")[-1]
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("Ошибка", show_alert=True)
        return

    _, msg = await user_service.mark_word(
        user, word_key, WordStatus.UNKNOWN, word_service=word_service
    )
    await callback.answer(msg[:200], show_alert=True)


@router.callback_query(F.data.startswith("word:examples:"))
async def word_examples(
    callback: CallbackQuery,
    word_service: WordService,
) -> None:
    """Показать примеры использования слова."""
    word_key = callback.data.split(":")[-1]
    word = word_service.get_by_key(word_key)
    if word is None:
        await callback.answer("Слово не найдено", show_alert=True)
        return

    await callback.message.answer(word_service.format_examples(word))
    await callback.answer()


@router.callback_query(F.data.startswith("word:dict:"))
async def word_add_dictionary(
    callback: CallbackQuery,
    session: AsyncSession,
    word_service: WordService,
) -> None:
    """Добавить слово в личный словарь (премиум)."""
    word_key = callback.data.split(":")[-1]
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)

    if user is None:
        await callback.answer("Ошибка", show_alert=True)
        return

    if not user_service.is_premium_active(user):
        await callback.answer(
            "📖 Личный словарь доступен в Premium! /premium",
            show_alert=True,
        )
        return

    _, msg = await user_service.mark_word(
        user, word_key, WordStatus.FAVORITE, word_service=word_service
    )
    await callback.answer(msg, show_alert=True)

    # Обновляем кнопку
    if callback.message.reply_markup:
        await callback.message.edit_reply_markup(
            reply_markup=word_actions_keyboard(word_key, in_dictionary=True)
        )
