"""
Общая инициализация бота для Vercel (serverless) и локального запуска.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from aiogram.types import BotCommand

from bot import create_bot, create_dispatcher
from config import Settings, get_settings
from database import init_db
from services.word_service import WordService

logger = logging.getLogger(__name__)

_cache: dict[str, Any] = {}
# Dispatcher создаётся один раз — роутеры нельзя подключать повторно
_dispatcher = None


class _LazyWordService:
    """Загружает words.json только при первом обращении (/start этого не требует)."""

    __slots__ = ("_path", "_impl")

    def __init__(self, path) -> None:
        self._path = path
        self._impl: WordService | None = None

    def _load(self) -> WordService:
        if self._impl is None:
            self._impl = WordService(self._path)
        return self._impl

    def __getattr__(self, name: str) -> Any:
        return getattr(self._load(), name)


async def ensure_database(settings: Settings) -> None:
    """Инициализирует БД и создаёт таблицы при первом запуске."""
    from database import ensure_database_ready

    await ensure_database_ready(settings)


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
        BotCommand(command="test_premium", description="🧪 Тест Premium (с кодом)"),
        BotCommand(command="support", description="💝 Поддержать проект"),
    ]
    await bot.set_my_commands(commands)


def _get_dispatcher():
    """Singleton Dispatcher; пересоздаётся после нового деплоя на Vercel."""
    global _dispatcher
    deploy_id = (
        os.getenv("VERCEL_GIT_COMMIT_SHA")
        or os.getenv("VERCEL_DEPLOYMENT_ID")
        or "local"
    )
    if _dispatcher is None or getattr(_dispatcher, "_deploy_id", None) != deploy_id:
        _dispatcher = create_dispatcher()
        _dispatcher._deploy_id = deploy_id
        logger.info("Dispatcher initialized deploy_id=%s", deploy_id[:12])
    return _dispatcher


async def get_application() -> tuple[Any, Any, WordService, Settings]:
    """
    Возвращает (bot, dispatcher, word_service, settings).

    На Vercel: Bot создаётся на запрос (сессия закрывается после webhook),
    словарь и схема БД кэшируются между запросами в одном инстансе.
    """
    is_vercel = bool(os.getenv("VERCEL"))

    if not is_vercel and "bot" in _cache:
        return _cache["bot"], _cache["dp"], _cache["word_service"], _cache["settings"]

    settings = _cache.get("settings") or get_settings()
    await ensure_database(settings)

    word_service = _cache.get("word_service")
    if word_service is None:
        word_service = _LazyWordService(settings.words_file)
        _cache["word_service"] = word_service
        _cache["settings"] = settings

    bot = create_bot(settings)
    dp = _get_dispatcher()
    dp.workflow_data.update(settings=settings, word_service=word_service)

    if not is_vercel:
        _cache.update(bot=bot, dp=dp, word_service=word_service, settings=settings)

    return bot, dp, word_service, settings
