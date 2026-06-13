"""
Инициализация бота aiogram 3.x и регистрация роутеров.
"""

from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import Settings
from handlers import get_all_routers
from utils.html_escape import h

logger = logging.getLogger(__name__)


def create_bot(settings: Settings) -> Bot:
    """Создаёт экземпляр Bot с HTML-разметкой по умолчанию."""
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    """Создаёт Dispatcher и подключает все роутеры."""
    import logging

    from aiogram.types import ErrorEvent

    dp = Dispatcher(storage=MemoryStorage())

    @dp.errors()
    async def global_error_handler(event: ErrorEvent, bot: Bot) -> None:
        logger.exception("Необработанная ошибка: %s", event.exception)
        update = event.update
        chat_id = None
        if update.message:
            chat_id = update.message.chat.id
        elif update.callback_query and update.callback_query.message:
            chat_id = update.callback_query.message.chat.id

        if chat_id:
            try:
                err = event.exception
                detail = f"{type(err).__name__}: {err}"
                logger.error("Handler error for chat %s: %s", chat_id, detail)
                await bot.send_message(
                    chat_id,
                    "⚠️ Произошла ошибка сервера.\n"
                    f"<code>{h(detail[:200])}</code>\n\n"
                    "Попробуйте /start снова.",
                )
            except Exception:
                logger.exception("Не удалось отправить сообщение об ошибке")

    for router in get_all_routers():
        dp.include_router(router)
        logger.debug("Подключён роутер: %s", router.name)

    return dp
