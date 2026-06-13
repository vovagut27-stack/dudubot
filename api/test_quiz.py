"""
Тест /quiz через production dispatcher. GET /api/test_quiz
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def _test_quiz() -> dict:
    from aiogram.types import Update
    from bootstrap import get_application

    bot, dp, _, _ = await get_application()

    payload = {
        "update_id": 1234567891,
        "message": {
            "message_id": 101,
            "date": 1700000000,
            "chat": {"id": 888777666, "type": "private"},
            "from": {
                "id": 888777666,
                "is_bot": False,
                "first_name": "TestQuiz",
                "username": "testquiz",
            },
            "text": "/quiz",
            "entities": [{"offset": 0, "length": 5, "type": "bot_command"}],
        },
    }

    errors: list[str] = []

    try:
        update = Update.model_validate(payload, context={"bot": bot})
        await dp.feed_update(bot, update)
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
    finally:
        if os.getenv("VERCEL"):
            await bot.session.close()

    return {"ok": len(errors) == 0, "errors": errors}


class handler(BaseHTTPRequestHandler):
    """GET /api/test_quiz"""

    def do_GET(self) -> None:
        try:
            result = asyncio.run(_test_quiz())
            body = json.dumps(result, ensure_ascii=False, indent=2)
            status = 200 if result.get("ok") else 500
        except Exception:
            body = json.dumps({"ok": False, "error": traceback.format_exc()}, ensure_ascii=False)
            status = 500

        self.send_response(status)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))
