"""
Работа с базой данных через SQLAlchemy 2.0.

Поддерживает:
- SQLite (aiosqlite) — локальная разработка
- PostgreSQL (asyncpg) — production
- Turso / libSQL (sqlalchemy-libsql) — облачная SQLite
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import Settings

logger = logging.getLogger(__name__)

engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def _create_turso_engine(settings: Settings) -> AsyncEngine:
    """
    Turso/libSQL.

    На Vercel — только remote (без embedded replica, /tmp ненадёжен).
    Локально — embedded replica для скорости.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.ext.asyncio import async_engine_from_sync_engine

    if os.getenv("VERCEL"):
        # Remote-only: sqlite+libsql://host?secure=true
        sync_engine = create_engine(
            f"sqlite+{settings.database_url}?secure=true",
            connect_args={"auth_token": settings.database_auth_token},
        )
        logger.info("Turso remote: %s", settings.database_url)
    else:
        settings.turso_embedded_path.parent.mkdir(parents=True, exist_ok=True)
        embedded = settings.turso_embedded_path.as_posix()
        sync_engine = create_engine(
            f"sqlite+libsql:///{embedded}",
            connect_args={
                "auth_token": settings.database_auth_token,
                "sync_url": settings.database_url,
            },
        )
        logger.info("Turso embedded=%s sync=%s", embedded, settings.database_url)

    return async_engine_from_sync_engine(sync_engine)


def init_db(settings: Settings) -> None:
    """Создаёт движок и фабрику сессий."""
    global engine, async_session_factory

    if settings.is_turso():
        engine = _create_turso_engine(settings)
    else:
        connect_args: dict = {}
        if settings.database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        engine = create_async_engine(
            settings.database_url,
            echo=False,
            connect_args=connect_args,
        )

    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency: выдаёт асинхронную сессию БД."""
    if async_session_factory is None:
        raise RuntimeError("База данных не инициализирована. Вызовите init_db().")

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def close_db() -> None:
    """Корректно закрывает пул соединений."""
    if engine is not None:
        await engine.dispose()
