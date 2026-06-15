"""
Выдача тестового Premium: GET /api/test_premium?secret=SETUP_SECRET&telegram_id=ID
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def _grant_premium(telegram_id: int, days: int) -> dict:
    from bootstrap import ensure_database
    from config import PREMIUM_TEST_DAYS, get_settings
    from database import session_scope
    from services.user_service import UserService

    settings = get_settings()
    await ensure_database(settings)

    grant_days = days if days > 0 else PREMIUM_TEST_DAYS

    async with session_scope() as session:
        user_service = UserService(session)
        user = await user_service.get_by_telegram_id(telegram_id)
        if user is None:
            user = await user_service.get_or_create(telegram_id=telegram_id)
        until = user_service.grant_test_premium(user, days=grant_days)

    return {
        "ok": True,
        "telegram_id": telegram_id,
        "premium_until": until.isoformat(),
        "days_granted": grant_days,
    }


class handler(BaseHTTPRequestHandler):
    """GET /api/test_premium?secret=...&telegram_id=123456789&days=30"""

    def do_GET(self) -> None:
        from api._setup_auth import verify_setup_secret

        if not verify_setup_secret(self):
            return

        query = parse_qs(urlparse(self.path).query)
        raw_id = (query.get("telegram_id") or [""])[0].strip()
        if not raw_id.isdigit():
            self.send_response(400)
            self.end_headers()
            self.wfile.write(
                b"Missing or invalid ?telegram_id= (numeric Telegram user ID)"
            )
            return

        days_raw = (query.get("days") or ["0"])[0].strip()
        try:
            days = int(days_raw) if days_raw else 0
        except ValueError:
            days = 0

        try:
            result = asyncio.run(_grant_premium(int(raw_id), days))
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
