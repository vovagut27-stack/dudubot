"""
Мини-квиз по выученным словам: /quiz
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import WordStatus
from services.user_service import UserService
from services.word_service import WordEntry, WordService
from utils.html_escape import h
from utils.keyboards import quiz_answer_keyboard
from utils.menu_filters import menu_btn

logger = logging.getLogger(__name__)
router = Router(name="quiz")

QUIZ_SIZE = 5


class QuizStates(StatesGroup):
    """FSM состояние квиза."""

    active = State()


@dataclass
class QuizSessionData:
    """Данные текущей сессии квиза в FSM."""

    questions: list[WordEntry] = field(default_factory=list)
    current: int = 0
    score: int = 0
    options_map: dict[str, str] = field(default_factory=dict)


@router.message(Command("quiz"))
@router.message(menu_btn("btn_quiz"))
async def cmd_quiz(
    message: Message,
    session: AsyncSession,
    word_service: WordService,
    state: FSMContext,
) -> None:
    """Запускает мини-квиз."""
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(message.from_user.id)

    if user is None or not user.onboarding_completed:
        await message.answer("Сначала пройдите онбординг: /start")
        return

    progress_list = await user_service.get_learned_words(user.id, limit=30)
    learned_keys = [
        p.word_key
        for p in progress_list
        if p.status in (WordStatus.LEARNED.value, WordStatus.FAVORITE.value)
    ]

    words: list[WordEntry] = []
    for key in learned_keys:
        w = word_service.get_by_key(key)
        if w:
            words.append(w)

    if len(words) < 3:
        await message.answer(
            "🎯 Для квиза нужно минимум 3 выученных слова.\n"
            "Отмечайте слова как «✅ Выучил» и возвращайтесь!"
        )
        return

    random.shuffle(words)
    questions = words[:QUIZ_SIZE]

    quiz = QuizSessionData(questions=questions)
    await state.set_state(QuizStates.active)
    await state.update_data(
        questions=[q.key for q in questions],
        current=0,
        score=0,
    )

    await _send_question(message, questions[0], word_service, state)


async def _send_question(
    message: Message,
    word: WordEntry,
    word_service: WordService,
    state: FSMContext,
) -> None:
    """Отправляет вопрос квиза."""
    wrong = word_service.pick_quiz_options(word, word.language, word.level, count=3)
    options_text = [word.translation] + wrong
    random.shuffle(options_text)

    options_map: dict[str, str] = {}
    buttons: list[tuple[str, str]] = []
    for i, opt in enumerate(options_text):
        suffix = f"{word.key}:{i}"
        options_map[suffix] = opt
        display = opt if len(opt) <= 40 else opt[:37] + "…"
        buttons.append((suffix, display))

    data = await state.get_data()
    current = data.get("current", 0)
    await state.update_data(options_map=options_map)

    await message.answer(
        f"🎯 Вопрос {current + 1}/{len(data.get('questions', []))}\n\n"
        f"Как переводится слово <b>{h(word.word)}</b>?",
        reply_markup=quiz_answer_keyboard(buttons),
    )


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

    score = data.get("score", 0)
    if selected == word.translation:
        score += 1
        await callback.answer("✅ Верно! +10 очков")
        user_service = UserService(session)
        user = await user_service.get_by_telegram_id(callback.from_user.id)
        if user:
            user.points += 10
            user.xp_level = word_service.calculate_level(user.points)
    else:
        await callback.answer(f"❌ Неверно. Ответ: {word.translation}", show_alert=True)

    current = data.get("current", 0) + 1
    questions_keys: list[str] = data.get("questions", [])

    if current >= len(questions_keys):
        user_service = UserService(session)
        user = await user_service.get_by_telegram_id(callback.from_user.id)
        if user:
            await user_service.save_quiz_result(user.id, score, len(questions_keys))

        await callback.message.edit_text(
            f"🏁 <b>Квиз завершён!</b>\n\n"
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
