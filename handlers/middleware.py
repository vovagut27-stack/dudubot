"""
Middleware: инъекция сессии БД в каждый handler.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database import rollback_session, session_scope

logger = logging.getLogger(__name__)


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
