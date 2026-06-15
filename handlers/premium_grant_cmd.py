"""Общая логика выдачи тестового Premium из команд бота."""

from __future__ import annotations

import logging

from aiogram.types import Message

from services.premium_grant import grant_test_premium_to

logger = logging.getLogger(__name__)


async def reply_premium_granted(message: Message, target_id: int) -> None:
    """Выдаёт Premium и отвечает пользователю."""
    status = await message.answer("⏳ Активирую Premium…")

    try:
        result = await grant_test_premium_to(target_id)
    except Exception:
        logger.exception("grant premium failed for %s", target_id)
        await status.edit_text(
            "❌ Не удалось выдать Premium.\n\n"
            "Попробуйте в браузере:\n"
            f"<code>/api/migrate?secret=...&grant_premium={target_id}</code>"
        )
        return

    until_str = result["premium_until"][:19].replace("T", " ")
    label = "вам" if target_id == message.from_user.id else f"ID <code>{target_id}</code>"

    if result.get("verified_active"):
        text = (
            f"✅ Premium выдан {label} до <b>{until_str} UTC</b>\n\n"
            "Проверьте: /stats · /dictionary · Premium-квизы в /quiz"
        )
    else:
        text = (
            f"⚠️ Premium записан {label} до <b>{until_str} UTC</b>, "
            "но проверка не прошла.\n"
            "Откройте /stats — если всё ещё Free, напишите создателю."
        )

    try:
        await status.edit_text(text)
    except Exception:
        await message.answer(text)
