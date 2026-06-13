"""
Webhook-эндпоинт: Telegram отправляет сюда все сообщения пользователей.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from aiogram.types import Update

logger = logging.getLogger(__name__)


async def _handle_webhook(body: bytes, secret_header: str | None) -> tuple[int, str]:
    """Обрабатывает входящий update от Telegram."""
    import time

    from bootstrap import get_application

    t0 = time.perf_counter()
    expected_secret = os.getenv("WEBHOOK_SECRET", "")
    if expected_secret and secret_header != expected_secret:
        logger.warning("Webhook 403: неверный WEBHOOK_SECRET")
        return 403, "Forbidden: WEBHOOK_SECRET mismatch"

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return 400, "Invalid JSON"

    update_id = payload.get("update_id")
    logger.info("Webhook update_id=%s", update_id)

    bot, dp, _, _ = await get_application()
    logger.info("Webhook init %.0f ms update_id=%s", (time.perf_counter() - t0) * 1000, update_id)
    try:
        update = Update.model_validate(payload, context={"bot": bot})
        await dp.feed_update(bot, update)
        logger.info(
            "Webhook ok %.0f ms update_id=%s",
            (time.perf_counter() - t0) * 1000,
            update_id,
        )
        return 200, "OK"
    finally:
        # На Vercel закрываем сессию после каждого запроса
        if os.getenv("VERCEL"):
            await bot.session.close()


class handler(BaseHTTPRequestHandler):
    """Vercel Serverless Function — POST /api/webhook"""

    def do_POST(self) -> None:
        secret = self.headers.get("X-Telegram-Bot-Api-Secret-Token")
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""

        try:
            status, message = asyncio.run(_handle_webhook(body, secret))
        except Exception:
            tb = traceback.format_exc()
            logger.error("Webhook error:\n%s", tb)
            status, message = 500, f"Error: {tb[-200:]}"

        self.send_response(status)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(message.encode("utf-8"))
