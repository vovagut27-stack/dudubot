"""
Работа с базой данных через SQLAlchemy 2.0.

Поддерживает:
- SQLite (aiosqlite) — локальная разработка
- PostgreSQL (asyncpg) — production
- Turso / libSQL — облако (на Vercel: sync + AsyncCompatSession)
"""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Union

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from config import Settings

logger = logging.getLogger(__name__)

engine: AsyncEngine | None = None
async_session_factory: async_sessionmaker[AsyncSession] | None = None

# Vercel + Turso: синхронный движок (async_engine_from_sync_engine недоступен на Vercel)
use_sync_sessions: bool = False
sync_session_factory: sessionmaker | None = None
turso_sync_engine = None


def _create_turso_sync_engine(settings: Settings):
    """Синхронный Turso remote engine — стабильно работает на Vercel."""
    from sqlalchemy import create_engine

    if os.getenv("VERCEL"):
        eng = create_engine(
            f"sqlite+{settings.database_url}?secure=true",
            connect_args={"auth_token": settings.database_auth_token},
        )
        logger.info("Turso remote (Vercel): %s", settings.database_url)
        return eng

    settings.turso_embedded_path.parent.mkdir(parents=True, exist_ok=True)
    embedded = settings.turso_embedded_path.as_posix()
    eng = create_engine(
        f"sqlite+libsql:///{embedded}",
        connect_args={
            "auth_token": settings.database_auth_token,
            "sync_url": settings.database_url,
        },
    )
    logger.info("Turso embedded=%s sync=%s", embedded, settings.database_url)
    return eng


def _create_turso_async_engine(settings: Settings) -> AsyncEngine:
    """Turso async через embedded replica (локально)."""
    from sqlalchemy import create_engine
    from sqlalchemy.ext.asyncio import async_engine_from_sync_engine

    sync_engine = _create_turso_sync_engine(settings)
    return async_engine_from_sync_engine(sync_engine)


def init_db(settings: Settings) -> None:
    """Создаёт движок и фабрику сессий."""
    global engine, async_session_factory, use_sync_sessions, sync_session_factory, turso_sync_engine

    if settings.is_turso() and os.getenv("VERCEL"):
        use_sync_sessions = True
        turso_sync_engine = _create_turso_sync_engine(settings)
        sync_session_factory = sessionmaker(turso_sync_engine, expire_on_commit=False)
        return

    use_sync_sessions = False
    sync_session_factory = None

    if settings.is_turso():
        engine = _create_turso_async_engine(settings)
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


SessionType = Union[AsyncSession, "AsyncCompatSession"]


async def _safe_commit(session: SessionType) -> None:
    """Commit или rollback, если транзакция уже отменена (PendingRollbackError)."""
    from sqlalchemy.exc import PendingRollbackError

    try:
        await session.commit()
    except PendingRollbackError:
        logger.warning("Сессия была отменена до commit — выполняем rollback")
        await session.rollback()
    except Exception:
        await session.rollback()
        raise


async def rollback_session(session: SessionType) -> None:
    """Откатывает транзакцию, игнорируя повторный rollback."""
    try:
        await session.rollback()
    except Exception:
        logger.debug("Rollback session failed", exc_info=True)


@asynccontextmanager
async def session_scope() -> AsyncGenerator[SessionType, None]:
    """Контекстный менеджер сессии — гарантирует commit/rollback."""
    if use_sync_sessions:
        from database_sync import AsyncCompatSession

        if sync_session_factory is None:
            raise RuntimeError("Sync session factory не инициализирована")
        session = AsyncCompatSession(sync_session_factory())
        try:
            yield session
            await _safe_commit(session)
        except Exception:
            await rollback_session(session)
            raise
        finally:
            await session.close()
        return

    if async_session_factory is None:
        raise RuntimeError("База данных не инициализирована. Вызовите init_db().")

    async with async_session_factory() as session:
        try:
            yield session
            await _safe_commit(session)
        except Exception:
            await rollback_session(session)
            raise


async def get_session() -> AsyncGenerator[SessionType, None]:
    """Dependency: выдаёт асинхронную сессию БД."""
    async with session_scope() as session:
        yield session


async def close_db() -> None:
    """Корректно закрывает пул соединений."""
    if engine is not None:
        await engine.dispose()


def _table_exists(conn, table: str) -> bool:
    from sqlalchemy import text

    return (
        conn.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:t"),
            {"t": table},
        ).fetchone()
        is not None
    )


def _table_columns(conn, table: str) -> set[str]:
    """Список колонок через PRAGMA — надёжнее inspect() на Turso/libSQL."""
    from sqlalchemy import text

    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def _run_schema_patches(conn) -> list[str]:
    """Применяет ALTER TABLE для недостающих колонок. Возвращает список добавленных."""
    from sqlalchemy import text

    applied: list[str] = []
    patches: list[tuple[str, str, str]] = [
        (
            "users",
            "ui_language",
            "ALTER TABLE users ADD COLUMN ui_language TEXT DEFAULT 'ru'",
        ),
    ]

    for table, column, ddl in patches:
        if not _table_exists(conn, table):
            continue
        if column in _table_columns(conn, table):
            continue
        try:
            conn.execute(text(ddl))
            applied.append(f"{table}.{column}")
            logger.info("Migration: added %s.%s", table, column)
        except Exception as exc:
            msg = str(exc).lower()
            if "duplicate column" in msg or "already exists" in msg:
                logger.info("Migration: %s.%s already present", table, column)
                continue
            raise

    return applied


def prepare_schema(bind) -> list[str]:
    """
    Создаёт таблицы (если их нет) и применяет миграции колонок.

    Одно соединение + AUTOCOMMIT — минимум round-trip к Turso на cold start.
    """
    from sqlalchemy.engine import Engine

    from models.models import Base

    engine = bind if isinstance(bind, Engine) else bind.engine

    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        if not _table_exists(conn, "users"):
            Base.metadata.create_all(bind=conn)
            logger.info("Created database tables")
        return _run_schema_patches(conn)


def migrate_schema(bind) -> list[str]:
    """Добавляет новые колонки в существующие таблицы (Turso/SQLite)."""
    from sqlalchemy.engine import Engine

    engine = bind if isinstance(bind, Engine) else bind.engine

    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
        if not _table_exists(conn, "users"):
            return []
        return _run_schema_patches(conn)
