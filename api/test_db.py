"""
Диагностика БД на Vercel: GET /api/test_db
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def _test_db() -> dict:
    from bootstrap import ensure_database
    from config import get_settings
    from database import session_scope
    from services.user_service import UserService

    settings = get_settings()
    await ensure_database(settings)

    async with session_scope() as session:
        svc = UserService(session)
        user = await svc.get_or_create(
            telegram_id=999888777,
            username="test_user",
            first_name="Test",
        )
        return {
            "ok": True,
            "user_telegram_id": user.telegram_id,
            "onboarding": user.onboarding_completed,
        }


class handler(BaseHTTPRequestHandler):
    """GET /api/test_db"""

    def do_GET(self) -> None:
        try:
            result = asyncio.run(_test_db())
            body = json.dumps(result, ensure_ascii=False, indent=2)
            status = 200
        except Exception:
            body = json.dumps(
                {"ok": False, "error": traceback.format_exc()},
                ensure_ascii=False,
            )
            status = 500

        self.send_response(status)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))
