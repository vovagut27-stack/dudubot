"""
Полный тест /start через dispatcher. GET /api/test_start
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def _test_start() -> dict:
    from aiogram.types import Update
    from bot import create_bot, create_dispatcher
    from config import get_settings

    settings = get_settings()
    bot = create_bot(settings)
    dp = create_dispatcher()  # отдельный dispatcher — не трогаем production singleton

    payload = {
        "update_id": 1234567890,
        "message": {
            "message_id": 100,
            "date": 1700000000,
            "chat": {"id": 888777666, "type": "private"},
            "from": {
                "id": 888777666,
                "is_bot": False,
                "first_name": "TestStart",
                "username": "teststart",
            },
            "text": "/start",
            "entities": [{"offset": 0, "length": 6, "type": "bot_command"}],
        },
    }

    errors: list[str] = []

    from aiogram.types import ErrorEvent

    @dp.errors()
    async def _capture(event: ErrorEvent, bot_instance) -> bool:
        errors.append(f"{type(event.exception).__name__}: {event.exception}")
        return True

    try:
        update = Update.model_validate(payload, context={"bot": bot})
        await dp.feed_update(bot, update)
    except Exception as exc:
        errors.append(f"feed_update: {type(exc).__name__}: {exc}")
    finally:
        await bot.session.close()

    return {"ok": len(errors) == 0, "errors": errors}


class handler(BaseHTTPRequestHandler):
    """GET /api/test_start"""

    def do_GET(self) -> None:
        try:
            result = asyncio.run(_test_start())
            body = json.dumps(result, ensure_ascii=False, indent=2)
            status = 200 if result.get("ok") else 500
        except Exception:
            body = json.dumps({"ok": False, "error": traceback.format_exc()}, ensure_ascii=False)
            status = 500

        self.send_response(status)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))
