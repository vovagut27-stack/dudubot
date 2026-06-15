"""
Админ-команды: тестовая выдача Premium.
"""

from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from config import PREMIUM_TEST_DAYS, Settings
from services.user_service import UserService

logger = logging.getLogger(__name__)
router = Router(name="admin")

PREMIUM_TEST_USAGE = (
    "🧪 <b>Тест Premium</b>\n\n"
    "Выдать себе:\n"
    "<code>/test_premium</code>\n\n"
    "Выдать другому (Telegram ID):\n"
    "<code>/test_premium 123456789</code>\n\n"
    f"Срок: <b>{PREMIUM_TEST_DAYS} дней</b> (продлевает, если Premium уже активен)."
)


def _is_admin(telegram_id: int, settings: Settings) -> bool:
    return telegram_id in settings.admin_ids


@router.message(Command("test_premium"))
async def cmd_test_premium(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    """Выдаёт тестовый Premium администратору или указанному пользователю."""
    if not message.from_user:
        return

    if not settings.admin_ids:
        await message.answer(
            "⚙️ ADMIN_IDS не настроен.\n"
            "Добавьте свой Telegram ID в переменную ADMIN_IDS на Vercel "
            "или используйте /api/test_premium?secret=..."
        )
        return

    if not _is_admin(message.from_user.id, settings):
        await message.answer("⛔ Команда только для администраторов (ADMIN_IDS).")
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) > 1 and parts[1].strip().lower() in {"help", "?", "-h"}:
        await message.answer(PREMIUM_TEST_USAGE)
        return

    target_id = message.from_user.id
    if len(parts) > 1:
        arg = parts[1].strip()
        if not arg.isdigit():
            await message.answer(PREMIUM_TEST_USAGE)
            return
        target_id = int(arg)

    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(target_id)
    if user is None:
        user = await user_service.get_or_create(telegram_id=target_id)

    until = user_service.grant_test_premium(user, days=PREMIUM_TEST_DAYS)
    until_str = until.strftime("%d.%m.%Y %H:%M UTC")

    label = "вам" if target_id == message.from_user.id else f"ID <code>{target_id}</code>"
    await message.answer(
        f"✅ Premium выдан {label} до <b>{until_str}</b>\n\n"
        "Проверьте: /stats · /dictionary · Premium-квизы в /quiz"
    )
