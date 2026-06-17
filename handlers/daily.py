"""
Ежедневное слово: /today, inline-действия, рассылка.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import DAILY_WORDS_FREE_PER_LANGUAGE, DAILY_WORDS_PREMIUM, SUPPORTED_LANGUAGES, Settings
from models.models import User, WordStatus
from services.dispatch_time import user_local_now
from services.user_service import UserService
from services.word_service import WordEntry, WordService
from utils.callback_guard import require_callback_message
from utils.callback_keys import word_key_from_callback
from utils.kb import word_actions_keyboard
from utils.menu_filters import menu_btn

logger = logging.getLogger(__name__)
router = Router(name="daily")


def _already_by_language(logs) -> dict[str, set[str]]:
    """Группирует отправленные сегодня слова по языку."""
    by_lang: dict[str, set[str]] = {}
    for log in logs:
        by_lang.setdefault(log.language, set()).add(log.word_key)
    return by_lang


async def send_daily_word_to_user(
    bot,
    user: User,
    session: AsyncSession,
    word_service: WordService,
    user_service: UserService,
    target_date: date | None = None,
    *,
    default_tz: str = "Europe/Moscow",
    notify_if_complete: bool = True,
) -> int:
    """
    Отправляет слова дня пользователю.

    Free: 3 слова на каждый изучаемый язык · Premium: 10 слов всего.

    Returns:
        Число успешно отправленных слов.
    """
    target_date = target_date or user_local_now(user, default_tz).date()
    languages = user_service.effective_language_list(user)
    is_premium = user_service.is_premium_active(user)
    limit = user_service.get_daily_word_limit(user)

    already_sent = await user_service.get_today_words(user, target_date)
    if len(already_sent) >= limit:
        if notify_if_complete:
            await bot.send_message(
                user.telegram_id,
                f"📬 Слова на сегодня уже отправлены ({len(already_sent)}/{limit}).\n"
                "Новые слова — завтра или оформите Premium для большего лимита.",
            )
        return 0

    sent_keys = {log.word_key for log in already_sent}
    remaining = limit - len(already_sent)
    already_by_lang = _already_by_language(already_sent)

    if is_premium:
        words = word_service.pick_daily_words(
            languages=languages,
            level=user.level,
            count=remaining + len(sent_keys),
            target_date=target_date,
            user_id=user.telegram_id,
        )
        words = [w for w in words if w.key not in sent_keys][:remaining]
    else:
        words = word_service.pick_daily_words_free(
            languages=languages,
            level=user.level,
            per_language=DAILY_WORDS_FREE_PER_LANGUAGE,
            already_by_lang=already_by_lang,
            target_date=target_date,
            user_id=user.telegram_id,
        )

    if not words:
        logger.warning("Нет слов для user=%s langs=%s", user.telegram_id, languages)
        if notify_if_complete:
            await bot.send_message(
                user.telegram_id,
                "😔 Не удалось подобрать слова. Попробуйте позже или смените уровень в /settings",
            )
        return 0

    if is_premium:
        plan = f"⭐ Premium ({DAILY_WORDS_PREMIUM} слов/день)"
    else:
        plan = (
            f"🆓 Free ({DAILY_WORDS_FREE_PER_LANGUAGE} слова × "
            f"{len(languages)} {_lang_word(len(languages))})"
        )

    total_today = len(already_sent) + len(words)
    await bot.send_message(
        chat_id=user.telegram_id,
        text=(
            f"📬 <b>Слова дня</b> — {total_today} из {limit}\n"
            f"{plan}\n"
            + ("" if is_premium else f"\n💡 Premium = <b>{DAILY_WORDS_PREMIUM} слов</b> /premium")
        ),
    )

    return await _deliver_words(bot, user, session, word_service, user_service, words, target_date)


def _lang_word(count: int) -> str:
    """Склонение «язык»."""
    if count % 10 == 1 and count % 100 != 11:
        return "язык"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return "языка"
    return "языков"


async def _deliver_words(
    bot,
    user: User,
    session: AsyncSession,
    word_service: WordService,
    user_service: UserService,
    words: list[WordEntry],
    target_date: date,
) -> int:
    """Отправляет список слов и логирует в БД. Возвращает число доставленных слов."""
    delivered = 0
    for idx, word in enumerate(words, start=1):
        try:
            progress = await user_service.get_word_progress(user.id, word.key)
            in_dict = progress is not None and progress.status == WordStatus.FAVORITE.value

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
            await session.flush()
            delivered += 1
            if idx < len(words):
                await asyncio.sleep(0.15)
        except Exception:
            logger.exception(
                "Не удалось отправить слово %s user=%s",
                word.key,
                user.telegram_id,
            )
    return delivered


async def _send_today_words(
    message: Message,
    session: AsyncSession,
    word_service: WordService,
    settings: Settings,
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
        default_tz=settings.timezone,
        notify_if_complete=True,
    )


@router.message(Command("today"))
@router.message(menu_btn("btn_today"))
async def cmd_today(
    message: Message,
    session: AsyncSession,
    word_service: WordService,
    settings: Settings,
) -> None:
    """Получить слово дня вручную."""
    try:
        await _send_today_words(message, session, word_service, settings)
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
    try:
        word_key = word_key_from_callback(callback.data, "word:learned:")
    except ValueError:
        await callback.answer("Ошибка данных", show_alert=True)
        return

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
    try:
        word_key = word_key_from_callback(callback.data, "word:unknown:")
    except ValueError:
        await callback.answer("Ошибка данных", show_alert=True)
        return

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
    try:
        word_key = word_key_from_callback(callback.data, "word:examples:")
    except ValueError:
        await callback.answer("Ошибка данных", show_alert=True)
        return

    word = word_service.get_by_key(word_key)
    if word is None:
        await callback.answer("Слово не найдено", show_alert=True)
        return

    msg = await require_callback_message(callback)
    if msg is None:
        return

    await msg.answer(word_service.format_examples(word))
    await callback.answer()


@router.callback_query(F.data.startswith("word:dict:"))
async def word_add_dictionary(
    callback: CallbackQuery,
    session: AsyncSession,
    word_service: WordService,
) -> None:
    try:
        word_key = word_key_from_callback(callback.data, "word:dict:")
    except ValueError:
        await callback.answer("Ошибка данных", show_alert=True)
        return

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

    chat_msg = await require_callback_message(callback)
    if chat_msg and chat_msg.reply_markup:
        await chat_msg.edit_reply_markup(
            reply_markup=word_actions_keyboard(word_key, in_dictionary=True)
        )

