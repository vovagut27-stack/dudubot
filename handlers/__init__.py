"""
Регистрация всех роутеров handlers.
"""

from __future__ import annotations

from aiogram import Router

from handlers.daily import router as daily_router
from handlers.dictionary import router as dictionary_router
from handlers.middleware import DatabaseMiddleware
from handlers.premium import router as premium_router
from handlers.quiz import router as quiz_router
from handlers.settings import router as settings_router
from handlers.start import router as start_router
from handlers.stats import router as stats_router


_middleware_attached = False


def get_all_routers() -> list[Router]:
    """Возвращает список роутеров с подключённым middleware."""
    global _middleware_attached
    routers = [
        start_router,
        daily_router,
        stats_router,
        settings_router,
        quiz_router,
        dictionary_router,
        premium_router,
    ]

    if not _middleware_attached:
        db_middleware = DatabaseMiddleware()
        for r in routers:
            r.message.middleware(db_middleware)
            r.callback_query.middleware(db_middleware)
            r.pre_checkout_query.middleware(db_middleware)
        _middleware_attached = True

    return routers
