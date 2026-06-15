"""
Vercel Cron: каждый час проверяет, кому пора отправить слова (07:00, 08:00, 09:00…).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

logger = logging.getLogger(__name__)


def _authorized(auth_header: str | None) -> bool:
    """Проверяет секрет Vercel Cron или CRON_SECRET."""
    cron_secret = os.getenv("CRON_SECRET", "")
    if not cron_secret:
        # Без секрета — разрешаем только если явно включено (не рекомендуется)
        return os.getenv("ALLOW_OPEN_CRON", "").lower() == "true"
    if auth_header == f"Bearer {cron_secret}":
        return True
    return False


async def _run_cron() -> dict:
    import os

    from bootstrap import get_application
    from services.daily_dispatch import run_daily_dispatch

    bot, _, word_service, settings = await get_application()
    try:
        return await run_daily_dispatch(bot, settings, word_service)
    finally:
        if os.getenv("VERCEL"):
            await bot.session.close()


class handler(BaseHTTPRequestHandler):
    """Vercel Serverless Function — GET /api/cron/daily"""

    def do_GET(self) -> None:
        if not _authorized(self.headers.get("Authorization")):
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"Unauthorized")
            return

        try:
            result = asyncio.run(_run_cron())
            body = json.dumps({"ok": True, **result})
            status = 200
        except Exception:
            logger.exception("Cron daily error")
            body = json.dumps({"ok": False, "error": "internal"})
            status = 500

        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))
