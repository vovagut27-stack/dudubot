"""
Обработчик /start и онбординг нового пользователя.
"""

from __future__ import annotations

import logging
from datetime import time

from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import CEFR_LEVELS, FREE_MAX_LANGUAGES, NOTIFICATION_TIMES, SUPPORTED_LANGUAGES
from services.user_service import UserService
from utils.callback_guard import require_callback_message
from utils.html_escape import h
from utils.callbacks import parse_time_callback
from utils.i18n import normalize_ui_language, supported_languages_list, t
from utils.kb import (
    main_menu_keyboard,
    onboarding_languages_keyboard,
    onboarding_level_keyboard,
    onboarding_time_keyboard,
)

logger = logging.getLogger(__name__)
router = Router(name="start")


class OnboardingStates(StatesGroup):
    """FSM-состояния онбординга."""

    level = State()
    languages = State()
    time = State()


def _welcome_text(ui_lang: str = "ru") -> str:
    """Приветственное сообщение онбординга."""
    lang = normalize_ui_language(ui_lang)
    return (
        f"{t(lang, 'welcome_title')}\n\n"
        f"{t(lang, 'welcome_body', languages=supported_languages_list())}"
    )


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Приветствие и начало онбординга или главное меню."""
    if not message.from_user:
        return

    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)

    ui = "ru"
    onboarding_done = False
    name = h(message.from_user.first_name) if message.from_user.first_name else "друг"

    try:
        user_service = UserService(session)
        user = await user_service.get_or_create(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
        )
        ui = normalize_ui_language(user.ui_language)
        onboarding_done = user.onboarding_completed
    except Exception:
        logger.exception("Ошибка БД при /start user=%s", message.from_user.id)
        await state.set_state(OnboardingStates.level)
        await message.answer(
            "👋 Добро пожаловать в «Слово Дня»!\n\nВыберите уровень:",
            reply_markup=onboarding_level_keyboard(),
            parse_mode=None,
        )
        return

    if onboarding_done:
        await message.answer(
            t(ui, "welcome_back", name=name),
            reply_markup=main_menu_keyboard(ui),
        )
        return

    await state.set_state(OnboardingStates.level)
    try:
        await message.answer(_welcome_text(ui), reply_markup=onboarding_level_keyboard())
    except Exception:
        logger.exception("Ошибка отправки приветствия user=%s", message.from_user.id)
        await message.answer(
            "Добро пожаловать! Выберите уровень:",
            reply_markup=onboarding_level_keyboard(),
            parse_mode=None,
        )


async def _reject_onboarded(callback: CallbackQuery, user) -> bool:
    """True — если онбординг уже завершён и callback нужно отклонить."""
    if user is not None and user.onboarding_completed:
        await callback.answer("Настройка уже завершена. Используйте /settings", show_alert=True)
        return True
    return False


@router.callback_query(F.data.startswith("onboard:level:"))
async def onboard_level(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Выбор уровня CEFR."""
    level = callback.data.split(":")[-1]
    if level not in CEFR_LEVELS:
        await callback.answer("Неверный уровень", show_alert=True)
        return

    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if await _reject_onboarded(callback, user):
        return
    ui = normalize_ui_language(user.ui_language) if user else "ru"

    msg = await require_callback_message(callback)
    if msg is None:
        return

    await state.update_data(level=level)
    await state.set_state(OnboardingStates.languages)
    await state.update_data(selected_langs=[])

    is_premium = user_service.is_premium_active(user) if user else False
    langs_hint = (
        t(ui, "onboard_choose_langs_premium")
        if is_premium
        else t(ui, "onboard_choose_langs_free", max=str(FREE_MAX_LANGUAGES))
    )

    await msg.edit_text(
        f"{t(ui, 'onboard_level_ok', level=level)}\n\n{langs_hint}",
        reply_markup=onboarding_languages_keyboard(set(), ui_lang=ui),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("onboard:lang:"))
async def onboard_language(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    """Переключение языка при онбординге."""
    code = callback.data.split(":")[-1]
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if await _reject_onboarded(callback, user):
        return
    ui = normalize_ui_language(user.ui_language) if user else "ru"

    if code == "done":
        data = await state.get_data()
        selected: list[str] = list(data.get("selected_langs", []))
        if not selected:
            await callback.answer(t(ui, "settings_select_lang"), show_alert=True)
            return
        await state.set_state(OnboardingStates.time)
        langs = ", ".join(SUPPORTED_LANGUAGES.get(c, c) for c in selected)
        msg = await require_callback_message(callback)
        if msg is None:
            return
        await msg.edit_text(
            f"{t(ui, 'onboard_langs_ok', langs=langs)}\n\n{t(ui, 'onboard_choose_time')}",
            reply_markup=onboarding_time_keyboard(),
        )
        await callback.answer()
        return

    if code not in SUPPORTED_LANGUAGES:
        await callback.answer("Неизвестный язык", show_alert=True)
        return

    data = await state.get_data()
    selected: list[str] = list(data.get("selected_langs", []))
    if code in selected:
        selected.remove(code)
    else:
        max_langs = user_service.max_study_languages(user) if user else FREE_MAX_LANGUAGES
        if max_langs is not None and len(selected) >= max_langs:
            await callback.answer(
                t(ui, "settings_langs_limit_free", max=str(max_langs)),
                show_alert=True,
            )
            return
        selected.append(code)
    await state.update_data(selected_langs=selected)

    msg = await require_callback_message(callback)
    if msg is None:
        return

    await msg.edit_reply_markup(
        reply_markup=onboarding_languages_keyboard(set(selected), ui_lang=ui)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("onboard:time:"))
async def onboard_time(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Завершение онбординга — сохранение настроек."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if await _reject_onboarded(callback, user):
        return

    try:
        hours, minutes, time_str = parse_time_callback(callback.data, "onboard:time:")
    except ValueError:
        await callback.answer("Неверное время", show_alert=True)
        return

    if time_str not in NOTIFICATION_TIMES:
        await callback.answer("Неверное время", show_alert=True)
        return

    data = await state.get_data()
    level = data.get("level")
    selected: list[str] = [
        code for code in data.get("selected_langs", []) if code in SUPPORTED_LANGUAGES
    ]

    if level not in CEFR_LEVELS or not selected:
        await callback.answer("Начните онбординг заново: /start", show_alert=True)
        await state.clear()
        return

    user = await user_service.get_or_create(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
    )
    max_langs = user_service.max_study_languages(user)
    if max_langs is not None and len(selected) > max_langs:
        ui = normalize_ui_language(user.ui_language)
        await callback.answer(
            t(ui, "settings_langs_limit_save", max=str(max_langs)),
            show_alert=True,
        )
        return
    await user_service.complete_onboarding(
        user=user,
        level=level,
        languages=sorted(selected),
        notification_time=time(hours, minutes),
    )
    await state.clear()

    ui = normalize_ui_language(user.ui_language)
    langs = ", ".join(SUPPORTED_LANGUAGES.get(c, c) for c in selected)
    msg = await require_callback_message(callback)
    if msg is None:
        return
    await msg.edit_text(
        t(ui, "onboard_done", level=level, langs=langs, time=time_str)
    )
    await msg.answer(
        t(ui, "onboard_main_menu"),
        reply_markup=main_menu_keyboard(ui),
    )
    await callback.answer("🚀")
