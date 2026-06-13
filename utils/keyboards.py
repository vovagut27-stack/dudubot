"""
Клавиатуры и inline-кнопки бота.
"""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from config import CEFR_LEVELS, SUPPORTED_LANGUAGES, SUPPORT_URL


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню после онбординга."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📚 Слово дня"),
                KeyboardButton(text="📊 Статистика"),
            ],
            [
                KeyboardButton(text="⚙️ Настройки"),
                KeyboardButton(text="🎯 Квиз"),
            ],
            [
                KeyboardButton(text="📖 Мой словарь"),
                KeyboardButton(text="⭐ Премиум"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие…",
    )


def onboarding_level_keyboard() -> InlineKeyboardMarkup:
    """Выбор уровня CEFR при онбординге."""
    rows = []
    row: list[InlineKeyboardButton] = []
    for i, level in enumerate(CEFR_LEVELS):
        row.append(
            InlineKeyboardButton(text=level, callback_data=f"onboard:level:{level}")
        )
        if (i + 1) % 3 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def onboarding_languages_keyboard(selected: set[str] | None = None) -> InlineKeyboardMarkup:
    """Мультивыбор языков при онбординге."""
    selected = selected or set()
    rows = []
    for code, label in SUPPORTED_LANGUAGES.items():
        mark = "✅ " if code in selected else ""
        rows.append([
            InlineKeyboardButton(
                text=f"{mark}{label}",
                callback_data=f"onboard:lang:{code}",
            )
        ])
    rows.append([
        InlineKeyboardButton(text="✔️ Готово", callback_data="onboard:lang:done"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def onboarding_time_keyboard() -> InlineKeyboardMarkup:
    """Выбор времени уведомлений."""
    times = ["07:00", "08:00", "09:00", "12:00", "18:00", "20:00", "21:00"]
    rows = []
    row: list[InlineKeyboardButton] = []
    for t in times:
        row.append(InlineKeyboardButton(text=t, callback_data=f"onboard:time:{t}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def word_actions_keyboard(word_key: str, *, in_dictionary: bool = False) -> InlineKeyboardMarkup:
    """Inline-кнопки под словом дня."""
    fav_text = "⭐ В избранном" if in_dictionary else "📖 В словарь"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Выучил", callback_data=f"word:learned:{word_key}"),
                InlineKeyboardButton(text="❌ Не знаю", callback_data=f"word:unknown:{word_key}"),
            ],
            [
                InlineKeyboardButton(text="💬 Примеры", callback_data=f"word:examples:{word_key}"),
                InlineKeyboardButton(text=fav_text, callback_data=f"word:dict:{word_key}"),
            ],
        ]
    )


def settings_keyboard() -> InlineKeyboardMarkup:
    """Меню настроек."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🕐 Время уведомлений", callback_data="settings:time")],
            [InlineKeyboardButton(text="📊 Уровень CEFR", callback_data="settings:level")],
            [InlineKeyboardButton(text="🌍 Языки", callback_data="settings:languages")],
            [InlineKeyboardButton(text="⭐ Премиум / Поддержка", callback_data="settings:premium")],
        ]
    )


def settings_level_keyboard() -> InlineKeyboardMarkup:
    """Изменение уровня в настройках."""
    rows = []
    row: list[InlineKeyboardButton] = []
    for i, level in enumerate(CEFR_LEVELS):
        row.append(InlineKeyboardButton(text=level, callback_data=f"settings:set_level:{level}"))
        if (i + 1) % 3 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="settings:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_time_keyboard() -> InlineKeyboardMarkup:
    """Изменение времени в настройках."""
    times = ["07:00", "08:00", "09:00", "12:00", "18:00", "20:00", "21:00"]
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for t in times:
        row.append(InlineKeyboardButton(text=t, callback_data=f"settings:set_time:{t}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="settings:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_languages_keyboard(selected: set[str]) -> InlineKeyboardMarkup:
    """Изменение языков в настройках."""
    rows = []
    for code, label in SUPPORTED_LANGUAGES.items():
        mark = "✅ " if code in selected else ""
        rows.append([
            InlineKeyboardButton(
                text=f"{mark}{label}",
                callback_data=f"settings:toggle_lang:{code}",
            )
        ])
    rows.append([InlineKeyboardButton(text="💾 Сохранить", callback_data="settings:save_langs")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data="settings:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def quiz_answer_keyboard(options: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    """
    Клавиатура ответов квиза.

    options: список (callback_suffix, текст кнопки)
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, callback_data=f"quiz:answer:{suffix}")]
            for suffix, text in options
        ]
    )


def premium_keyboard() -> InlineKeyboardMarkup:
    """Кнопки премиума и поддержки."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Оформить Premium", callback_data="premium:subscribe")],
            [InlineKeyboardButton(text="💝 Поддержать проект", url=SUPPORT_URL)],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="settings:back")],
        ]
    )


def dictionary_keyboard(words: list[tuple[str, str]], page: int, total_pages: int) -> InlineKeyboardMarkup:
    """
    Пагинация личного словаря.

    words: список (word_key, отображаемый текст)
    """
    rows = [
        [InlineKeyboardButton(text=text, callback_data=f"dict:view:{key}")]
        for key, text in words
    ]
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"dict:page:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="dict:noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"dict:page:{page + 1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)
