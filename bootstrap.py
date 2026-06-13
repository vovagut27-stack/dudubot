"""
Общая инициализация бота для Vercel (serverless) и локального запуска.
"""

from __future__ import annotations

import logging
from typing import Any

from aiogram.types import BotCommand

from bot import create_bot, create_dispatcher
from config import Settings, get_settings
from database import init_db
from models.models import Base
from services.word_service import WordService

logger = logging.getLogger(__name__)

# Кэш для «тёплых» serverless-инстансов Vercel
_cache: dict[str, Any] = {}


async def ensure_database(settings: Settings) -> None:
    """Инициализирует БД и создаёт таблицы при первом запуске."""
    from database import engine

    init_db(settings)
    if engine is not None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


async def set_bot_commands(bot) -> None:
    """Регистрирует команды в меню Telegram."""
    commands = [
        BotCommand(command="start", description="🚀 Начать / онбординг"),
        BotCommand(command="today", description="📚 Слово сегодня"),
        BotCommand(command="stats", description="📊 Статистика"),
        BotCommand(command="settings", description="⚙️ Настройки"),
        BotCommand(command="quiz", description="🎯 Мини-квиз"),
        BotCommand(command="dictionary", description="📖 Мой словарь"),
        BotCommand(command="premium", description="⭐ Премиум подписка"),
        BotCommand(command="support", description="💝 Поддержать проект"),
    ]
    await bot.set_my_commands(commands)


async def get_application() -> tuple[Any, Any, WordService, Settings]:
    """
    Возвращает (bot, dispatcher, word_service, settings).

    На Vercel повторно использует объекты в рамках одного инстанса.
    """
    if "bot" in _cache:
        return _cache["bot"], _cache["dp"], _cache["word_service"], _cache["settings"]

    settings = get_settings()
    await ensure_database(settings)

    word_service = WordService(settings.words_file)
    bot = create_bot(settings)
    dp = create_dispatcher()
    dp.workflow_data.update(settings=settings, word_service=word_service)

    _cache.update(bot=bot, dp=dp, word_service=word_service, settings=settings)
    return bot, dp, word_service, settings
