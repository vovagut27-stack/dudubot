"""
Мини-квиз: /quiz — базовый (Free) и Premium-режимы.
"""

from __future__ import annotations

import logging
import random
from enum import StrEnum

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import (
    QUIZ_POINTS_BASIC,
    QUIZ_POINTS_PREMIUM,
    QUIZ_SIZE_BASIC,
    QUIZ_SIZE_EXTENDED,
    QUIZ_SIZE_MULTILANG,
    QUIZ_SIZE_REVERSE,
    SUPPORTED_LANGUAGES,
)
from models.models import User, WordStatus
from services.user_service import UserService
from services.word_service import WordEntry, WordService
from utils.html_escape import h
from utils.kb import quiz_answer_keyboard, quiz_menu_keyboard
from utils.menu_filters import menu_btn

logger = logging.getLogger(__name__)
router = Router(name="quiz")

PREMIUM_MODES = frozenset({"extended", "reverse", "multilang"})

QUIZ_MODE_TITLES = {
    "basic": "📝 Базовый квиз",
    "extended": "📚 Расширенный квиз",
    "reverse": "🔄 Обратный квиз",
    "multilang": "🌍 Мультиязычный квиз",
}


class QuizMode(StrEnum):
    BASIC = "basic"
    EXTENDED = "extended"
    REVERSE = "reverse"
    MULTILANG = "multilang"


class QuizStates(StatesGroup):
    """FSM-состояние квиза."""

    active = State()


def _quiz_size(mode: str) -> int:
    return {
        QuizMode.BASIC: QUIZ_SIZE_BASIC,
        QuizMode.EXTENDED: QUIZ_SIZE_EXTENDED,
        QuizMode.REVERSE: QUIZ_SIZE_REVERSE,
        QuizMode.MULTILANG: QUIZ_SIZE_MULTILANG,
    }.get(mode, QUIZ_SIZE_BASIC)


def _points_per_answer(mode: str) -> int:
    return QUIZ_POINTS_PREMIUM if mode in PREMIUM_MODES else QUIZ_POINTS_BASIC


async def _collect_learned_words(
    user_service: UserService,
    word_service: WordService,
    user: User,
) -> list[WordEntry]:
    progress_list = await user_service.get_learned_words(user.id, limit=80)
    words: list[WordEntry] = []
    for progress in progress_list:
        if progress.status not in (WordStatus.LEARNED.value, WordStatus.FAVORITE.value):
            continue
        word = word_service.get_by_key(progress.word_key)
        if word:
            words.append(word)
    return words


def _build_questions(
    mode: str,
    user: User,
    word_service: WordService,
    learned: list[WordEntry],
) -> list[WordEntry] | None:
    size = _quiz_size(mode)

    if mode == QuizMode.MULTILANG:
        langs = user.language_list() or ["en"]
        pool = word_service.sample_quiz_vocabulary(langs, user.level, size * 2)
        if len(pool) < 4:
            return None
        random.shuffle(pool)
        return pool[:size]

    if len(learned) < 3:
        return None
    random.shuffle(learned)
    return learned[:size]


@router.message(Command("quiz"))
@router.message(menu_btn("btn_quiz"))
async def cmd_quiz(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    """Меню выбора типа квиза."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(message.from_user.id)

    if user is None or not user.onboarding_completed:
        await message.answer("Сначала пройдите онбординг: /start")
        return

    await state.clear()
    is_premium = user_service.is_premium_active(user)
    premium_hint = (
        "\n\n⭐ <b>Premium:</b> расширенный, обратный и мультиязычный квизы."
        if not is_premium
        else ""
    )
    await message.answer(
        "🎯 <b>Выберите тип квиза</b>\n\n"
        "📝 <b>Базовый</b> — перевод выученных слов (5 вопросов)\n"
        "📚 <b>Расширенный</b> — 10 вопросов по выученным словам\n"
        "🔄 <b>Обратный</b> — угадайте слово по переводу\n"
        "🌍 <b>Мультиязычный</b> — слова всех ваших языков на вашем уровне"
        f"{premium_hint}",
        reply_markup=quiz_menu_keyboard(is_premium=is_premium),
    )


@router.callback_query(F.data.startswith("quiz:start:"))
async def quiz_start(
    callback: CallbackQuery,
    session: AsyncSession,
    word_service: WordService,
    state: FSMContext,
) -> None:
    """Запуск выбранного квиза."""
    mode = callback.data.split(":")[-1]
    if mode not in {m.value for m in QuizMode}:
        await callback.answer("Неизвестный режим", show_alert=True)
        return

    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None or not user.onboarding_completed:
        await callback.answer("Сначала /start", show_alert=True)
        return

    if mode in PREMIUM_MODES and not user_service.is_premium_active(user):
        await callback.answer(
            "⭐ Этот квиз доступен в Premium! Оформите: /premium",
            show_alert=True,
        )
        return

    learned = await _collect_learned_words(user_service, word_service, user)
    questions = _build_questions(mode, user, word_service, learned)

    if questions is None:
        if mode == QuizMode.MULTILANG:
            await callback.answer(
                "Недостаточно слов в словаре для ваших языков и уровня.",
                show_alert=True,
            )
        else:
            await callback.answer(
                "Нужно минимум 3 выученных слова. Отмечайте «✅ Выучил»!",
                show_alert=True,
            )
        return

    reverse = mode == QuizMode.REVERSE
    await state.set_state(QuizStates.active)
    await state.update_data(
        questions=[q.key for q in questions],
        quiz_mode=mode,
        reverse=reverse,
        current=0,
        score=0,
    )

    title = QUIZ_MODE_TITLES.get(mode, "Квиз")
    await callback.message.edit_text(f"🎯 <b>{title}</b>\n\nПоехали!")
    await _send_question(callback.message, questions[0], word_service, state)
    await callback.answer()


async def _send_question(
    message: Message,
    word: WordEntry,
    word_service: WordService,
    state: FSMContext,
) -> None:
    """Отправляет вопрос квиза."""
    data = await state.get_data()
    reverse = data.get("reverse", False)
    lang_label = SUPPORTED_LANGUAGES.get(word.language, word.language)

    if reverse:
        wrong = word_service.pick_quiz_word_options(
            word, word.language, word.level, count=3
        )
        options_text = [word.word] + wrong
        question = (
            f"🎯 Вопрос {data.get('current', 0) + 1}/{len(data.get('questions', []))}\n"
            f"🌍 {lang_label}\n\n"
            f"Какое слово означает: <b>{h(word.translation)}</b>?"
        )
    else:
        wrong = word_service.pick_quiz_options(
            word, word.language, word.level, count=3
        )
        options_text = [word.translation] + wrong
        question = (
            f"🎯 Вопрос {data.get('current', 0) + 1}/{len(data.get('questions', []))}\n"
            f"🌍 {lang_label}\n\n"
            f"Как переводится слово <b>{h(word.word)}</b>?"
        )

    random.shuffle(options_text)

    options_map: dict[str, str] = {}
    buttons: list[tuple[str, str]] = []
    for i, opt in enumerate(options_text):
        suffix = f"{word.key}:{i}"
        options_map[suffix] = opt
        display = opt if len(opt) <= 40 else opt[:37] + "…"
        buttons.append((suffix, display))

    await state.update_data(options_map=options_map)
    await message.answer(question, reply_markup=quiz_answer_keyboard(buttons))


@router.callback_query(F.data.startswith("quiz:answer:"), QuizStates.active)
async def quiz_answer(
    callback: CallbackQuery,
    session: AsyncSession,
    word_service: WordService,
    state: FSMContext,
) -> None:
    """Обработка ответа в квизе."""
    suffix = callback.data.replace("quiz:answer:", "")
    data = await state.get_data()
    options_map: dict[str, str] = data.get("options_map", {})
    selected = options_map.get(suffix, "")

    word_key = suffix.rsplit(":", 1)[0]
    word = word_service.get_by_key(word_key)
    if word is None:
        await callback.answer("Ошибка")
        return

    reverse = data.get("reverse", False)
    quiz_mode = data.get("quiz_mode", QuizMode.BASIC)
    correct_answer = word.word if reverse else word.translation
    points = _points_per_answer(quiz_mode)

    score = data.get("score", 0)
    if selected == correct_answer:
        score += 1
        await callback.answer(f"✅ Верно! +{points} очков")
        user_service = UserService(session)
        user = await user_service.get_by_telegram_id(callback.from_user.id)
        if user:
            user.points += points
            user.xp_level = word_service.calculate_level(user.points)
    else:
        await callback.answer(
            f"❌ Неверно. Ответ: {correct_answer}",
            show_alert=True,
        )

    current = data.get("current", 0) + 1
    questions_keys: list[str] = data.get("questions", [])

    if current >= len(questions_keys):
        user_service = UserService(session)
        user = await user_service.get_by_telegram_id(callback.from_user.id)
        if user:
            await user_service.save_quiz_result(user.id, score, len(questions_keys))

        mode_title = QUIZ_MODE_TITLES.get(quiz_mode, "Квиз")
        await callback.message.edit_text(
            f"🏁 <b>{mode_title} завершён!</b>\n\n"
            f"Результат: <b>{score}/{len(questions_keys)}</b>\n"
            f"{'🌟 Отлично!' if score >= len(questions_keys) * 0.8 else '💪 Продолжайте учиться!'}"
        )
        await state.clear()
        return

    await state.update_data(current=current, score=score)
    next_word = word_service.get_by_key(questions_keys[current])
    if next_word:
        await callback.message.delete()
        await _send_question(callback.message, next_word, word_service, state)
