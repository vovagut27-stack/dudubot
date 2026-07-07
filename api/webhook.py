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

WORD_CALLBACK_HINTS = {
    "word:ai:": "Готовлю AI-разбор...",
}


async def _early_ack_callback(payload: dict) -> None:
    """Отвечает на callback до тяжёлой инициализации (cold start Vercel > 10s)."""
    raw = payload.get("callback_query")
    if not raw:
        return

    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        return

    from aiogram import Bot
    from aiogram.types import CallbackQuery

    from utils.callback_guard import answer_callback

    data = raw.get("data") or ""
    if not data.startswith("word:"):
        return

    hint = next(
        (text for prefix, text in WORD_CALLBACK_HINTS.items() if data.startswith(prefix)),
        None,
    )

    bot = Bot(token=token)
    try:
        callback = CallbackQuery.model_validate(raw, context={"bot": bot})
        await answer_callback(callback, hint)
    except Exception:
        logger.exception("Early callback ack failed data=%s", data[:80])
    finally:
        await bot.session.close()


async def _run_catchup(
    update: Update,
    bot,
    word_service,
    settings,
    update_id: int | None,
) -> None:
    try:
        from services.dispatch_catchup import try_catchup_daily_words

        if update.message:
            await try_catchup_daily_words(update.message, bot, word_service, settings)
        elif update.callback_query:
            await try_catchup_daily_words(
                update.callback_query, bot, word_service, settings
            )
    except Exception:
        logger.exception("Catch-up dispatch failed update_id=%s", update_id)


async def _handle_webhook(body: bytes, secret_header: str | None) -> tuple[int, str]:
    """Обрабатывает входящий update от Telegram."""
    import time

    from bootstrap import get_application

    t0 = time.perf_counter()
    expected_secret = os.getenv("WEBHOOK_SECRET", "").strip()
    if os.getenv("VERCEL") and not expected_secret:
        logger.error("WEBHOOK_SECRET не задан на Vercel")
        return 503, "Webhook misconfigured: WEBHOOK_SECRET required"
    token = (secret_header or "").strip()
    if expected_secret and token != expected_secret:
        logger.warning(
            "Webhook 403: неверный WEBHOOK_SECRET (got %d chars, expected %d)",
            len(token),
            len(expected_secret),
        )
        return 403, "Forbidden: WEBHOOK_SECRET mismatch — откройте /api/setup?secret=..."

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return 400, "Invalid JSON"

    update_id = payload.get("update_id")
    logger.info("Webhook update_id=%s", update_id)

    await _early_ack_callback(payload)

    bot, dp, word_service, settings = await get_application()
    logger.info("Webhook init %.0f ms update_id=%s", (time.perf_counter() - t0) * 1000, update_id)

    update: Update | None = None
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
        if update is not None:
            await _run_catchup(update, bot, word_service, settings, update_id)
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
