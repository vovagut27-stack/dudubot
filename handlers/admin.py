"""
Админ-команды: тестовая выдача Premium.
"""

from __future__ import annotations

import logging
import os

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import PREMIUM_TEST_DAYS, Settings
from services.premium_grant import grant_test_premium_to

logger = logging.getLogger(__name__)
router = Router(name="admin")

PREMIUM_TEST_USAGE = (
    "🧪 <b>Тест Premium</b>\n\n"
    "<b>Способ 1</b> — секрет (без ADMIN_IDS):\n"
    "<code>/test_premium ВАШ_SETUP_SECRET</code>\n\n"
    "<b>Способ 2</b> — другому пользователю:\n"
    "<code>/test_premium TELEGRAM_ID ВАШ_SETUP_SECRET</code>\n\n"
    "<b>Способ 3</b> — если настроен ADMIN_IDS:\n"
    "<code>/test_premium</code> или <code>/test_premium ID</code>\n\n"
    f"Срок: <b>{PREMIUM_TEST_DAYS} дней</b>."
)


def _is_admin(telegram_id: int, settings: Settings) -> bool:
    return telegram_id in settings.admin_ids


def _check_secret(token: str) -> bool:
    expected = os.getenv("SETUP_SECRET", "")
    return bool(expected) and token == expected


def _parse_test_premium_args(
    text: str | None,
    from_user_id: int,
    settings: Settings,
) -> tuple[bool, int, str | None]:
    """
    Разбирает аргументы /test_premium.

    Returns:
        (authorized, target_telegram_id, error_hint)
    """
    parts = (text or "").split()
    target_id = from_user_id

    if len(parts) == 1:
        if _is_admin(from_user_id, settings):
            return True, target_id, None
        return False, target_id, "no_admin"

    if len(parts) == 2:
        arg = parts[1].strip()
        if _check_secret(arg):
            return True, from_user_id, None
        if arg.isdigit() and _is_admin(from_user_id, settings):
            return True, int(arg), None
        if arg.isdigit():
            return False, int(arg), "no_admin"
        return False, from_user_id, "bad_secret"

    if len(parts) >= 3:
        arg_id = parts[1].strip()
        arg_secret = parts[2].strip()
        if arg_id.isdigit() and _check_secret(arg_secret):
            return True, int(arg_id), None
        return False, from_user_id, "bad_args"

    return False, from_user_id, "bad_args"


@router.message(Command("test_premium"))
async def cmd_test_premium(
    message: Message,
    settings: Settings,
) -> None:
    """Выдаёт тестовый Premium администратору или по SETUP_SECRET."""
    if not message.from_user:
        return

    if len((message.text or "").split()) > 1 and (message.text or "").split()[1].lower() in {
        "help",
        "?",
        "-h",
    }:
        await message.answer(PREMIUM_TEST_USAGE)
        return

    ok, target_id, hint = _parse_test_premium_args(
        message.text,
        message.from_user.id,
        settings,
    )

    if not ok:
        if hint == "no_admin":
            await message.answer(
                "⛔ Нет доступа.\n\n"
                "Добавьте свой ID в ADMIN_IDS на Vercel\n"
                "или используйте:\n"
                "<code>/test_premium ВАШ_SETUP_SECRET</code>\n\n"
                + PREMIUM_TEST_USAGE
            )
        elif hint == "bad_secret":
            await message.answer("❌ Неверный секрет. Проверьте SETUP_SECRET.")
        else:
            await message.answer(PREMIUM_TEST_USAGE)
        return

    try:
        result = await grant_test_premium_to(target_id)
    except Exception:
        logger.exception("test_premium failed for %s", target_id)
        await message.answer("❌ Не удалось выдать Premium. Попробуйте через /api/migrate?grant_premium=...")
        return

    if not result.get("verified_active"):
        await message.answer(
            "⚠️ Premium записан в БД, но проверка не прошла.\n"
            f"<code>{result}</code>\n\n"
            "Проверьте: /api/premium_status?secret=...&telegram_id="
            f"{target_id}"
        )
        return

    until_str = result["premium_until"][:19].replace("T", " ")
    label = "вам" if target_id == message.from_user.id else f"ID <code>{target_id}</code>"
    await message.answer(
        f"✅ Premium выдан {label} до <b>{until_str} UTC</b>\n\n"
        "Проверьте: /stats · /dictionary · Premium-квизы в /quiz"
    )
