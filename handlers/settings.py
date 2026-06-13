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

from config import SUPPORTED_LANGUAGES, UI_LANGUAGES
from models.models import User
from services.user_service import UserService
from utils.callbacks import parse_time_callback
from utils.i18n import normalize_ui_language, t
from utils.keyboards import (
    main_menu_keyboard,
    settings_keyboard,
    settings_languages_keyboard,
    settings_level_keyboard,
    settings_time_keyboard,
    settings_ui_language_keyboard,
)
from utils.menu_filters import menu_btn

logger = logging.getLogger(__name__)
router = Router(name="settings")


class SettingsStates(StatesGroup):
    """FSM для редактирования языков."""

    languages = State()


def _settings_text(user: User) -> str:
    """Текст экрана настроек на языке пользователя."""
    ui = normalize_ui_language(user.ui_language)
    langs = ", ".join(SUPPORTED_LANGUAGES.get(c, c) for c in user.language_list())
    ui_name = UI_LANGUAGES.get(ui, ui)
    return (
        f"{t(ui, 'settings_title')}\n\n"
        f"{t(ui, 'settings_level_line', level=user.level)}\n"
        f"{t(ui, 'settings_langs_line', langs=langs)}\n"
        f"{t(ui, 'settings_ui_line', ui_lang=ui_name)}\n"
        f"{t(ui, 'settings_time_line', time=user.notification_time.strftime('%H:%M'))}"
    )


@router.message(Command("settings"))
@router.message(menu_btn("btn_settings"))
async def cmd_settings(message: Message, session: AsyncSession) -> None:
    """Меню настроек."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(message.from_user.id)

    if user is None or not user.onboarding_completed:
        await message.answer(t("ru", "onboard_first"))
        return

    ui = normalize_ui_language(user.ui_language)
    await message.answer(
        _settings_text(user),
        reply_markup=settings_keyboard(ui),
    )


@router.callback_query(F.data == "settings:back")
async def settings_back(
    callback: CallbackQuery,
    session: AsyncSession,
    *,
    skip_answer: bool = False,
) -> None:
    """Возврат в меню настроек."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        if not skip_answer:
            await callback.answer(t("ru", "error_generic"))
        return

    ui = normalize_ui_language(user.ui_language)
    await callback.message.edit_text(
        _settings_text(user),
        reply_markup=settings_keyboard(ui),
    )
    if not skip_answer:
        await callback.answer()


@router.callback_query(F.data == "settings:level")
async def settings_level_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    """Выбор уровня."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    ui = normalize_ui_language(user.ui_language) if user else "ru"

    await callback.message.edit_text(
        t(ui, "settings_choose_level"),
        reply_markup=settings_level_keyboard(ui),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:set_level:"))
async def settings_set_level(callback: CallbackQuery, session: AsyncSession) -> None:
    """Сохранение уровня."""
    level = callback.data.split(":")[-1]
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    ui = normalize_ui_language(user.ui_language) if user else "ru"
    if user:
        user.level = level
    await callback.answer(t(ui, "settings_level_saved", level=level))
    await settings_back(callback, session, skip_answer=True)


@router.callback_query(F.data == "settings:time")
async def settings_time_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    """Выбор времени."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    ui = normalize_ui_language(user.ui_language) if user else "ru"

    await callback.message.edit_text(
        t(ui, "settings_choose_time"),
        reply_markup=settings_time_keyboard(ui),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:set_time:"))
async def settings_set_time(callback: CallbackQuery, session: AsyncSession) -> None:
    """Сохранение времени уведомлений."""
    h, m, time_str = parse_time_callback(callback.data, "settings:set_time:")
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    ui = normalize_ui_language(user.ui_language) if user else "ru"
    if user:
        user.notification_time = time(h, m)
    await callback.answer(t(ui, "settings_time_saved", time=time_str))
    await settings_back(callback, session, skip_answer=True)


@router.callback_query(F.data == "settings:languages")
async def settings_langs_menu(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    """Мультивыбор языков для изучения."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    selected = set(user.language_list()) if user else set()
    ui = normalize_ui_language(user.ui_language) if user else "ru"

    await state.set_state(SettingsStates.languages)
    await state.update_data(selected_langs=list(selected))

    await callback.message.edit_text(
        t(ui, "settings_choose_langs"),
        reply_markup=settings_languages_keyboard(selected, ui_lang=ui),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:toggle_lang:"))
async def settings_toggle_lang(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Переключение языка в настройках."""
    code = callback.data.split(":")[-1]
    data = await state.get_data()
    selected: list[str] = list(data.get("selected_langs", []))
    if code in selected:
        selected.remove(code)
    else:
        selected.append(code)
    await state.update_data(selected_langs=selected)

    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    ui = normalize_ui_language(user.ui_language) if user else "ru"

    await callback.message.edit_reply_markup(
        reply_markup=settings_languages_keyboard(set(selected), ui_lang=ui)
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

    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    ui = normalize_ui_language(user.ui_language) if user else "ru"

    if not selected:
        await callback.answer(t(ui, "settings_select_lang"), show_alert=True)
        return

    if user:
        user.languages = ",".join(sorted(selected))

    await state.clear()
    await callback.answer(t(ui, "settings_langs_saved"))
    await settings_back(callback, session, skip_answer=True)


@router.callback_query(F.data == "settings:ui_language")
async def settings_ui_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    """Выбор языка интерфейса."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer(t("ru", "error_generic"))
        return

    ui = normalize_ui_language(user.ui_language)
    await callback.message.edit_text(
        t(ui, "settings_choose_ui"),
        reply_markup=settings_ui_language_keyboard(ui),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:set_ui:"))
async def settings_set_ui(callback: CallbackQuery, session: AsyncSession) -> None:
    """Сохранение языка интерфейса."""
    code = callback.data.split(":")[-1]
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer(t("ru", "error_generic"))
        return

    user.ui_language = normalize_ui_language(code)
    ui = user.ui_language
    lang_name = UI_LANGUAGES.get(ui, ui)

    await callback.answer(t(ui, "settings_ui_saved", ui_name=lang_name))
    await callback.message.edit_text(
        _settings_text(user),
        reply_markup=settings_keyboard(ui),
    )
    await callback.message.answer(
        t(ui, "onboard_main_menu"),
        reply_markup=main_menu_keyboard(ui),
    )
