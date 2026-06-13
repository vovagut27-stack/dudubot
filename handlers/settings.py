"""
Настройки пользователя: /settings
"""

from __future__ import annotations

import logging
from datetime import time

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import SUPPORTED_LANGUAGES
from services.user_service import UserService
from utils.callbacks import parse_time_callback
from utils.keyboards import (
    settings_keyboard,
    settings_languages_keyboard,
    settings_level_keyboard,
    settings_time_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="settings")


class SettingsStates(StatesGroup):
    """FSM для редактирования языков."""

    languages = State()


@router.message(Command("settings"))
@router.message(F.text == "⚙️ Настройки")
async def cmd_settings(message: Message, session: AsyncSession) -> None:
    """Меню настроек."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(message.from_user.id)

    if user is None or not user.onboarding_completed:
        await message.answer("Сначала пройдите онбординг: /start")
        return

    langs = ", ".join(SUPPORTED_LANGUAGES.get(c, c) for c in user.language_list())
    await message.answer(
        "⚙️ <b>Настройки</b>\n\n"
        f"📊 Уровень: <b>{user.level}</b>\n"
        f"🌍 Языки: {langs}\n"
        f"🕐 Уведомления: <b>{user.notification_time.strftime('%H:%M')}</b>",
        reply_markup=settings_keyboard(),
    )


@router.callback_query(F.data == "settings:back")
async def settings_back(callback: CallbackQuery, session: AsyncSession) -> None:
    """Возврат в меню настроек."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("Ошибка")
        return

    langs = ", ".join(SUPPORTED_LANGUAGES.get(c, c) for c in user.language_list())
    await callback.message.edit_text(
        "⚙️ <b>Настройки</b>\n\n"
        f"📊 Уровень: <b>{user.level}</b>\n"
        f"🌍 Языки: {langs}\n"
        f"🕐 Уведомления: <b>{user.notification_time.strftime('%H:%M')}</b>",
        reply_markup=settings_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "settings:level")
async def settings_level_menu(callback: CallbackQuery) -> None:
    """Выбор уровня."""
    await callback.message.edit_text(
        "📊 Выберите уровень CEFR:",
        reply_markup=settings_level_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:set_level:"))
async def settings_set_level(callback: CallbackQuery, session: AsyncSession) -> None:
    """Сохранение уровня."""
    level = callback.data.split(":")[-1]
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user:
        user.level = level
    await callback.answer(f"Уровень: {level} ✅")
    await settings_back(callback, session)


@router.callback_query(F.data == "settings:time")
async def settings_time_menu(callback: CallbackQuery) -> None:
    """Выбор времени."""
    await callback.message.edit_text(
        "🕐 Выберите время уведомлений:",
        reply_markup=settings_time_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:set_time:"))
async def settings_set_time(callback: CallbackQuery, session: AsyncSession) -> None:
    """Сохранение времени уведомлений."""
    h, m, time_str = parse_time_callback(callback.data, "settings:set_time:")
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user:
        user.notification_time = time(h, m)
    await callback.answer(f"Время: {time_str} ✅")
    await settings_back(callback, session)


@router.callback_query(F.data == "settings:languages")
async def settings_langs_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Мультивыбор языков."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    selected = set(user.language_list()) if user else set()

    await state.set_state(SettingsStates.languages)
    await state.update_data(selected_langs=list(selected))

    await callback.message.edit_text(
        "🌍 Выберите языки (можно несколько):",
        reply_markup=settings_languages_keyboard(selected),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:toggle_lang:"))
async def settings_toggle_lang(callback: CallbackQuery, state: FSMContext) -> None:
    """Переключение языка в настройках."""
    code = callback.data.split(":")[-1]
    data = await state.get_data()
    selected: list[str] = list(data.get("selected_langs", []))
    if code in selected:
        selected.remove(code)
    else:
        selected.append(code)
    await state.update_data(selected_langs=selected)
    await callback.message.edit_reply_markup(
        reply_markup=settings_languages_keyboard(set(selected))
    )
    await callback.answer()


@router.callback_query(F.data == "settings:save_langs")
async def settings_save_langs(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Сохранение выбранных языков."""
    data = await state.get_data()
    selected: list[str] = list(data.get("selected_langs", []))
    if not selected:
        await callback.answer("Выберите хотя бы один язык!", show_alert=True)
        return

    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user:
        user.languages = ",".join(sorted(selected))

    await state.clear()
    await callback.answer("Языки сохранены ✅")
    await settings_back(callback, session)
