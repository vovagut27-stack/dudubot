"""Защита от callback без message (inline в каналах, устаревшие кнопки)."""

from __future__ import annotations

import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

logger = logging.getLogger(__name__)


def _callback_expired(exc: TelegramBadRequest) -> bool:
    text = str(exc).lower()
    return "query is too old" in text or "query id is invalid" in text


async def answer_callback(
    callback: CallbackQuery,
    text: str | None = None,
    *,
    show_alert: bool = False,
) -> bool:
    """
    Отвечает на callback в пределах 10-секундного окна Telegram.

    Returns:
        False если query уже протух (ответ невозможен).
    """
    try:
        await callback.answer(text, show_alert=show_alert)
        return True
    except TelegramBadRequest as exc:
        msg = str(exc).lower()
        if _callback_expired(exc):
            logger.warning("Callback expired: data=%s", callback.data)
            return False
        if "already" in msg and "answer" in msg:
            return True
        raise


async def answer_callback_or_message(
    callback: CallbackQuery,
    text: str,
    *,
    show_alert: bool = False,
) -> None:
    """Toast через callback или обычное сообщение, если query уже закрыт."""
    if await answer_callback(callback, text, show_alert=show_alert):
        return
    chat_msg = callback.message
    if chat_msg is not None:
        await chat_msg.answer(text)


async def require_callback_message(callback: CallbackQuery) -> Message | None:
    """Возвращает message или None (и отвечает на callback)."""
    if callback.message is None:
        await answer_callback(callback)
        return None
    return callback.message
