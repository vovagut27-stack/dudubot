"""
Middleware: инъекция сессии БД и контекста приложения в каждый handler.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database import rollback_session, session_scope

logger = logging.getLogger(__name__)


def _ensure_app_context(data: dict[str, Any]) -> None:
    """Подставляет settings/word_service из кэша bootstrap без нового Bot."""
    if "settings" in data and "word_service" in data:
        return

    from bootstrap import _LazyWordService, _cache
    from config import get_settings

    settings = _cache.get("settings") or get_settings()
    word_service = _cache.get("word_service")
    if word_service is None:
        word_service = _LazyWordService(settings.words_file)
        _cache["word_service"] = word_service
        _cache["settings"] = settings

    data.setdefault("settings", settings)
    data.setdefault("word_service", word_service)


class AppContextMiddleware(BaseMiddleware):
    """Гарантирует settings и word_service в data (workflow_data на serverless)."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        _ensure_app_context(data)
        return await handler(event, data)


class DatabaseMiddleware(BaseMiddleware):
    """Открывает сессию SQLAlchemy на время обработки update."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with session_scope() as session:
            data["session"] = session
            try:
                return await handler(event, data)
            except Exception:
                await rollback_session(session)
                raise
