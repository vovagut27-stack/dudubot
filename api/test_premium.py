"""
Выдача тестового Premium: GET /api/test_premium?secret=SETUP_SECRET&telegram_id=ID

Дубликат: /api/migrate?secret=...&grant_premium=ID
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


class handler(BaseHTTPRequestHandler):
    """GET /api/test_premium?secret=...&telegram_id=123456789&days=30"""

    def do_GET(self) -> None:
        from api._setup_auth import verify_setup_secret

        if not verify_setup_secret(self):
            return

        query = parse_qs(urlparse(self.path).query)
        raw_id = (query.get("telegram_id") or query.get("grant_premium") or [""])[0].strip()
        if not raw_id.isdigit():
            self.send_response(400)
            self.end_headers()
            self.wfile.write(
                b"Missing ?telegram_id= or ?grant_premium= (numeric Telegram user ID)"
            )
            return

        days_raw = (query.get("days") or ["0"])[0].strip()
        try:
            days = int(days_raw) if days_raw else 0
        except ValueError:
            days = 0

        try:
            from services.premium_grant import grant_test_premium_to

            result = asyncio.run(
                grant_test_premium_to(int(raw_id), days=days if days > 0 else None)
            )
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
