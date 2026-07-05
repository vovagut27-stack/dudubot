"""
Адаптер sync-сессии SQLAlchemy под async-handlers (для Vercel + Turso).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy.orm import Session


class AsyncCompatSession:
    """Оборачивает синхронную Session — handlers могут использовать await."""

    def __init__(self, session: Session) -> None:
        self._session = session

    async def execute(self, statement: Any, *args: Any, **kwargs: Any) -> Any:
        return await asyncio.to_thread(
            self._session.execute, statement, *args, **kwargs
        )

    async def commit(self) -> None:
        await asyncio.to_thread(self._session.commit)

    async def rollback(self) -> None:
        await asyncio.to_thread(self._session.rollback)

    async def flush(self) -> None:
        await asyncio.to_thread(self._session.flush)

    @asynccontextmanager
    async def begin_nested(self) -> AsyncGenerator[Any, None]:
        """Async wrapper for a SAVEPOINT transaction."""
        transaction = await asyncio.to_thread(self._session.begin_nested)
        try:
            yield transaction
        except Exception:
            await asyncio.to_thread(transaction.rollback)
            raise
        else:
            await asyncio.to_thread(transaction.commit)

    def add(self, obj: Any) -> None:
        self._session.add(obj)

    async def close(self) -> None:
        await asyncio.to_thread(self._session.close)

    async def __aenter__(self) -> "AsyncCompatSession":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
