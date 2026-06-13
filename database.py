"""
Асинхронная работа с базой данных через SQLAlchemy 2.0.

Поддерживает SQLite (по умолчанию) и PostgreSQL через DATABASE_URL.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config import Settings

# Глобальные объекты инициализируются при старте приложения
engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(settings: Settings) -> None:
    """
    Создаёт движок и фабрику сессий.

    Вызывается один раз при запуске бота.
    """
    global engine, async_session_factory

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
