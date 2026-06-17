"""
Vercel Cron / GitHub Actions: каждый час проверяет, кому пора отправить слова.
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
        from api._cron_auth import verify_cron_request

        if not verify_cron_request(self):
            self.send_response(401)
            self.end_headers()
            self.wfile.write(
                b"Unauthorized — set CRON_SECRET on Vercel or use Bearer SETUP_SECRET"
            )
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
