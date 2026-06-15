"""
Админ-команды: тестовая выдача Premium.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from config import PREMIUM_TEST_DAYS, Settings
from handlers.premium_grant_cmd import reply_premium_granted
from utils.setup_auth import check_setup_secret

logger = logging.getLogger(__name__)
router = Router(name="admin")

PREMIUM_TEST_USAGE = (
    "🧪 <b>Тест Premium</b>\n\n"
    "Отправьте <b>одним сообщением</b>:\n"
    "<code>/test_premium ВАШ_КОД</code>\n\n"
    "Или сначала <code>/test_premium</code>, "
    "затем код отдельным сообщением.\n\n"
    "Также работает:\n"
    "<code>/premium ВАШ_КОД</code>\n\n"
    "Другому пользователю:\n"
    "<code>/test_premium TELEGRAM_ID ВАШ_КОД</code>\n\n"
    f"Срок: <b>{PREMIUM_TEST_DAYS} дней</b>."
)


def _is_admin(telegram_id: int, settings: Settings) -> bool:
    return telegram_id in settings.admin_ids


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
        return False, target_id, "need_secret"

    if len(parts) == 2:
        arg = parts[1].strip()
        if check_setup_secret(arg):
            return True, from_user_id, None
        if arg.isdigit() and _is_admin(from_user_id, settings):
            return True, int(arg), None
        if arg.isdigit():
            return False, int(arg), "no_admin"
        return False, from_user_id, "bad_secret"

    if len(parts) >= 3:
        arg_id = parts[1].strip()
        arg_secret = parts[2].strip()
        if arg_id.isdigit() and check_setup_secret(arg_secret):
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
        if hint == "need_secret":
            await message.answer(
                "🔑 Отправьте код активации <b>следующим сообщением</b>\n"
                "или одной строкой:\n"
                "<code>/test_premium ВАШ_КОД</code>\n\n"
                + PREMIUM_TEST_USAGE
            )
        elif hint == "no_admin":
            await message.answer(
                "⛔ Нет доступа.\n\n"
                "Используйте:\n"
                "<code>/test_premium ВАШ_КОД</code>\n\n"
                + PREMIUM_TEST_USAGE
            )
        elif hint == "bad_secret":
            await message.answer("❌ Неверный код. Проверьте SETUP_SECRET.")
        else:
            await message.answer(PREMIUM_TEST_USAGE)
        return

    await reply_premium_granted(message, target_id)


@router.message(F.text.func(lambda t: bool(t) and not t.strip().startswith("/") and check_setup_secret(t)))
async def cmd_secret_as_text(message: Message) -> None:
    """Код SETUP_SECRET отдельным сообщением (после /test_premium или /premium)."""
    if not message.from_user:
        return
    await reply_premium_granted(message, message.from_user.id)
