"""
Личный словарь (Premium): /dictionary
"""

from __future__ import annotations

import logging
import math

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from services.user_service import UserService
from services.word_service import WordService
from utils.i18n import normalize_ui_language
from utils.menu_filters import menu_btn

logger = logging.getLogger(__name__)
router = Router(name="dictionary")

PAGE_SIZE = 8


async def _show_dictionary_page(
    target: Message,
    session: AsyncSession,
    word_service: WordService,
    telegram_id: int,
    page: int = 0,
    *,
    edit: bool = False,
) -> None:
    """Отображает страницу личного словаря."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(telegram_id)

    if user is None:
        return

    if not user_service.is_premium_active(user):
        text = (
            "📖 <b>Личный словарь</b> — Premium функция\n\n"
            "⭐ С Premium вы можете:\n"
            "• Сохранять слова в избранное\n"
            "• Просматривать свой словарь\n"
            "• Учить слова повторно\n\n"
            "Оформите подписку через Telegram Stars!"
        )
        ui = normalize_ui_language(user.ui_language)
        if edit:
            await target.edit_text(text, reply_markup=premium_keyboard(ui))
        else:
            await target.answer(text, reply_markup=premium_keyboard(ui))
        return

    progress = await user_service.get_learned_words(user.id, limit=200)
    if not progress:
        await target.answer(
            "📖 Ваш словарь пока пуст.\n"
            "Добавляйте слова кнопкой «📖 В словарь» под словом дня!"
        )
        return

    total_pages = max(1, math.ceil(len(progress) / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))
    chunk = progress[page * PAGE_SIZE : (page + 1) * PAGE_SIZE]

    items: list[tuple[str, str]] = []
    for p in chunk:
        word = word_service.get_by_key(p.word_key)
        if word:
            emoji = "⭐" if p.status == "favorite" else "✅"
            items.append((word.key, f"{emoji} {word.word} — {word.translation[:30]}"))

    text = f"📖 <b>Мой словарь</b> ({len(progress)} слов)"
    kb = dictionary_keyboard(items, page, total_pages)

    if edit:
        await target.edit_text(text, reply_markup=kb)
    else:
        await target.answer(text, reply_markup=kb)


@router.message(Command("dictionary"))
@router.message(menu_btn("btn_dictionary"))
async def cmd_dictionary(
    message: Message,
    session: AsyncSession,
    word_service: WordService,
) -> None:
    """Открывает личный словарь."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(message.from_user.id)

    if user is None or not user.onboarding_completed:
        await message.answer("Сначала пройдите онбординг: /start")
        return

    await _show_dictionary_page(
        message, session, word_service, message.from_user.id
    )


@router.callback_query(F.data.startswith("dict:page:"))
async def dict_page(
    callback: CallbackQuery,
    session: AsyncSession,
    word_service: WordService,
) -> None:
    """Пагинация словаря."""
    page = int(callback.data.split(":")[-1])
    await _show_dictionary_page(
        callback.message,
        session,
        word_service,
        callback.from_user.id,
        page,
        edit=True,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("dict:view:"))
async def dict_view_word(
    callback: CallbackQuery,
    word_service: WordService,
) -> None:
    """Просмотр слова из словаря."""
    word_key = callback.data.split(":")[-1]
    word = word_service.get_by_key(word_key)
    if word is None:
        await callback.answer("Слово не найдено", show_alert=True)
        return

    from utils.keyboards import word_actions_keyboard

    await callback.message.answer(
        word_service.format_word_message(word, header="📖 Из словаря"),
        reply_markup=word_actions_keyboard(word_key, in_dictionary=True),
    )
    await callback.answer()


@router.callback_query(F.data == "dict:noop")
async def dict_noop(callback: CallbackQuery) -> None:
    """Заглушка для кнопки номера страницы."""
    await callback.answer()
