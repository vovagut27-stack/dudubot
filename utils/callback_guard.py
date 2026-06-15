"""Защита от callback без message (inline в каналах, устаревшие кнопки)."""

from __future__ import annotations

from aiogram.types import CallbackQuery, Message


async def require_callback_message(callback: CallbackQuery) -> Message | None:
    """Возвращает message или None (и отвечает на callback)."""
    if callback.message is None:
        await callback.answer()
        return None
    return callback.message
