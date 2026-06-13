"""
Middleware: инъекция сессии БД в каждый handler.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database import get_session


class DatabaseMiddleware(BaseMiddleware):
    """Открывает сессию SQLAlchemy на время обработки update."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async for session in get_session():
            data["session"] = session
            return await handler(event, data)
        return None
