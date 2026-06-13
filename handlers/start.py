"""
Обработчик /start и онбординг нового пользователя.
"""

from __future__ import annotations

import logging
from datetime import time

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import SUPPORTED_LANGUAGES
from services.user_service import UserService
from utils.keyboards import (
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


WELCOME_TEXT = (
    "👋 <b>Добро пожаловать в «Слово Дня»!</b>\n\n"
    "Каждый день вы будете получать новое слово на выбранных языках:\n"
    "🇬🇧 English · 🇷🇸 Српски · 🇷🇺 Русский · 🇧🇾 Беларуская\n\n"
    "🎮 Зарабатывайте очки, поддерживайте streak и проходите квизы!\n\n"
    "Давайте настроим ваш профиль 👇"
)


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext) -> None:
    """Приветствие и начало онбординга или главное меню."""
    user_service = UserService(session)
    user = await user_service.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    if user.onboarding_completed:
        await message.answer(
            f"С возвращением, {message.from_user.first_name or 'друг'}! 🌟\n"
            "Используйте меню или команды.",
            reply_markup=main_menu_keyboard(),
        )
        return

    await state.set_state(OnboardingStates.level)
    await message.answer(WELCOME_TEXT, reply_markup=onboarding_level_keyboard())


@router.callback_query(F.data.startswith("onboard:level:"))
async def onboard_level(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор уровня CEFR."""
    level = callback.data.split(":")[-1]
    await state.update_data(level=level)
    await state.set_state(OnboardingStates.languages)
    await state.update_data(selected_langs=[])

    await callback.message.edit_text(
        f"✅ Уровень: <b>{level}</b>\n\n"
        "🌍 Выберите один или несколько языков для изучения:",
        reply_markup=onboarding_languages_keyboard(set()),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("onboard:lang:"))
async def onboard_language(callback: CallbackQuery, state: FSMContext) -> None:
    """Переключение языка при онбординге."""
    code = callback.data.split(":")[-1]

    if code == "done":
        data = await state.get_data()
        selected: list[str] = list(data.get("selected_langs", []))
        if not selected:
            await callback.answer("Выберите хотя бы один язык!", show_alert=True)
            return
        await state.set_state(OnboardingStates.time)
        langs = ", ".join(SUPPORTED_LANGUAGES.get(c, c) for c in selected)
        await callback.message.edit_text(
            f"🌍 Языки: {langs}\n\n"
            "🕐 В какое время присылать слово дня?",
            reply_markup=onboarding_time_keyboard(),
        )
        await callback.answer()
        return

    data = await state.get_data()
    selected: list[str] = list(data.get("selected_langs", []))
    if code in selected:
        selected.remove(code)
    else:
        selected.append(code)
    await state.update_data(selected_langs=selected)

    await callback.message.edit_reply_markup(
        reply_markup=onboarding_languages_keyboard(set(selected))
    )
    await callback.answer()


@router.callback_query(F.data.startswith("onboard:time:"))
async def onboard_time(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Завершение онбординга — сохранение настроек."""
    time_str = callback.data.split(":")[-1]
    hours, minutes = map(int, time_str.split(":"))

    data = await state.get_data()
    level = data.get("level", "A1")
    selected: list[str] = list(data.get("selected_langs", ["en"]))

    user_service = UserService(session)
    user = await user_service.get_or_create(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
    )
    await user_service.complete_onboarding(
        user=user,
        level=level,
        languages=sorted(selected),
        notification_time=time(hours, minutes),
    )
    await state.clear()

    langs = ", ".join(SUPPORTED_LANGUAGES.get(c, c) for c in selected)
    await callback.message.edit_text(
        "🎉 <b>Настройка завершена!</b>\n\n"
        f"📊 Уровень: <b>{level}</b>\n"
        f"🌍 Языки: {langs}\n"
        f"🕐 Уведомления: <b>{time_str}</b>\n\n"
        "Нажмите /today чтобы получить первое слово!"
    )
    await callback.message.answer(
        "Главное меню 👇",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer("Готово! 🚀")
