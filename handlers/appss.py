"""
Верификация бота в каталоге @appss: /appss_verify
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import APPSS_VERIFY_CODE

router = Router(name="appss")


@router.message(Command("appss_verify"))
async def cmd_appss_verify(message: Message) -> None:
    """Отвечает кодом верификации для каталога Appss."""
    if not APPSS_VERIFY_CODE:
        await message.answer("Код верификации Appss не настроен.")
        return
    await message.answer(APPSS_VERIFY_CODE)
