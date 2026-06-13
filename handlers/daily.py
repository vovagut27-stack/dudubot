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

from config import DAILY_WORDS_FREE, DAILY_WORDS_PREMIUM, SUPPORTED_LANGUAGES
from models.models import User, WordStatus
from services.user_service import UserService
from services.word_service import WordEntry, WordService
from utils.keyboards import word_actions_keyboard
from utils.menu_filters import menu_btn

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
    Отправляет слова дня пользователю.

    Free: 3 слова · Premium: 10 слов (распределены по выбранным языкам).
    """
    target_date = target_date or date.today()
    languages = user.language_list() or ["en"]
    is_premium = user_service.is_premium_active(user)
    limit = DAILY_WORDS_PREMIUM if is_premium else DAILY_WORDS_FREE

    words = word_service.pick_daily_words(
        languages=languages,
        level=user.level,
        count=limit,
        target_date=target_date,
        user_id=user.telegram_id,
    )

    if not words:
        logger.warning("Нет слов для user=%s langs=%s", user.telegram_id, languages)
        await bot.send_message(
            user.telegram_id,
            "😔 Не удалось подобрать слова. Попробуйте позже или смените уровень в /settings",
        )
        return

    plan = "⭐ Premium" if is_premium else f"🆓 Free ({DAILY_WORDS_FREE} слова/день)"
    await bot.send_message(
        chat_id=user.telegram_id,
        text=(
            f"📬 <b>Слова дня</b> — {len(words)} из {limit}\n"
            f"{plan}\n"
            + ("" if is_premium else f"\n💡 Premium = <b>{DAILY_WORDS_PREMIUM} слов</b> /premium")
        ),
    )

    for idx, word in enumerate(words, start=1):
        progress = await user_service.get_word_progress(user.id, word.key)
        in_dict = progress is not None and progress.status in (
            WordStatus.FAVORITE.value,
            WordStatus.LEARNED.value,
        )

        lang_label = SUPPORTED_LANGUAGES.get(word.language, word.language)
        header = f"📚 {idx}/{len(words)} · {lang_label}"
        text = word_service.format_word_message(
            word, header=header, index=idx, total=len(words)
        )

        msg = await bot.send_message(
            chat_id=user.telegram_id,
            text=text,
            reply_markup=word_actions_keyboard(word.key, in_dictionary=in_dict),
        )
        await user_service.log_daily_word(
            user=user,
            word_key=word.key,
            language=word.language,
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
@router.message(menu_btn("btn_today"))
async def cmd_today(message: Message, session: AsyncSession, word_service: WordService) -> None:
    """Получить слово дня вручную."""
    try:
        await _send_today_words(message, session, word_service)
    except Exception:
        from database import rollback_session

        await rollback_session(session)
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
