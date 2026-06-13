"""
Точка входа: запуск Telegram-бота «Слово Дня».
"""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram.types import BotCommand

from bot import create_bot, create_dispatcher
from config import get_settings
from database import close_db, init_db
from scheduler import DailyScheduler
from services.word_service import WordService


def setup_logging(level: str) -> None:
    """Настраивает формат логирования."""
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


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
        BotCommand(command="support", description="💝 Поддержать проект"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    """Главная корутина приложения."""
    settings = get_settings()
    setup_logging(settings.log_level)

    logger = logging.getLogger(__name__)
    logger.info("Запуск бота «Слово Дня»…")

    init_db(settings)

    # Создаём таблицы при первом запуске (для prod используйте alembic upgrade head)
    from models.models import Base
    from database import engine

    if engine is not None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    word_service = WordService(settings.words_file)

    bot = create_bot(settings)
    dp = create_dispatcher()

    # Передаём зависимости через workflow_data
    dp.workflow_data.update(
        settings=settings,
        word_service=word_service,
    )

    scheduler = DailyScheduler(bot, settings, word_service)
    scheduler.start()

    await set_bot_commands(bot)

    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await close_db()
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
