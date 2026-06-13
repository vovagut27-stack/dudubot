"""
Планировщик ежедневной рассылки слов (APScheduler).
"""

from __future__ import annotations

import logging
from datetime import date

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import async_sessionmaker

from config import Settings
from services.daily_dispatch import run_daily_dispatch
from services.word_service import WordService

logger = logging.getLogger(__name__)


class DailyScheduler:
    """Управляет cron-задачами рассылки."""

    def __init__(
        self,
        bot: Bot,
        settings: Settings,
        word_service: WordService,
    ) -> None:
        self._bot = bot
        self._settings = settings
        self._word_service = word_service
        self._scheduler = AsyncIOScheduler(timezone=settings.timezone)

    def start(self) -> None:
        """Запускает планировщик — проверка каждую минуту."""
        self._scheduler.add_job(
            self._tick,
            CronTrigger(minute="*"),
            id="daily_word_tick",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self._scheduler.start()
        logger.info("Планировщик запущен (timezone=%s)", self._settings.timezone)

    def shutdown(self) -> None:
        """Останавливает планировщик."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("Планировщик остановлен")

    async def _tick(self) -> None:
        """Каждую минуту ищет пользователей для рассылки."""
        from services.daily_dispatch import run_daily_dispatch

        await run_daily_dispatch(self._bot, self._settings, self._word_service)
