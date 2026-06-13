"""
Однократная регистрация webhook в Telegram (откройте в браузере после деплоя).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aiogram.types import WebhookInfo


async def _setup_webhook() -> dict:
    """Регистрирует webhook — БД не нужна."""
    from bot import create_bot
    from bootstrap import set_bot_commands
    from config import get_settings

    settings = get_settings()
    bot = create_bot(settings)
    await set_bot_commands(bot)

    vercel_url = (
        os.getenv("WEBHOOK_BASE_URL")
        or os.getenv("VERCEL_PROJECT_PRODUCTION_URL")
        or os.getenv("VERCEL_URL")
        or ""
    )
    if not vercel_url:
        raise ValueError(
            "Задайте WEBHOOK_BASE_URL=https://dudubot-ten.vercel.app в Vercel env"
        )

    if not vercel_url.startswith("https://"):
        vercel_url = f"https://{vercel_url}"

    webhook_url = f"{vercel_url.rstrip('/')}/api/webhook"
    secret = os.getenv("WEBHOOK_SECRET", "")

    await bot.set_webhook(
        url=webhook_url,
        secret_token=secret or None,
        drop_pending_updates=True,
    )

    info: WebhookInfo = await bot.get_webhook_info()
    await bot.session.close()

    return {
        "webhook_url": webhook_url,
        "telegram_url": info.url,
        "pending_updates": info.pending_update_count,
    }


class handler(BaseHTTPRequestHandler):
    """GET /api/setup?secret=ВАШ_SETUP_SECRET"""

    def do_GET(self) -> None:
        from urllib.parse import parse_qs, urlparse

        query = parse_qs(urlparse(self.path).query)
        secret = (query.get("secret") or [""])[0]
        expected = os.getenv("SETUP_SECRET", "")

        if not expected or secret != expected:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden: wrong or missing ?secret=")
            return

        try:
            result = asyncio.run(_setup_webhook())
            body = json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2)
            status = 200
        except Exception as exc:
            body = json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
            status = 500

        self.send_response(status)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))
