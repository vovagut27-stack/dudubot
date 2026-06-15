"""
Выдача Premium: GET /api/grant_premium?secret=SETUP_SECRET&telegram_id=ID
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
    """GET /api/grant_premium?secret=...&telegram_id=123456789&days=30"""

    def do_GET(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        secret = (query.get("secret") or [""])[0]
        expected = os.getenv("SETUP_SECRET", "")

        if not expected or secret != expected:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden: wrong or missing ?secret=")
            return

        raw_id = (query.get("telegram_id") or query.get("grant_premium") or [""])[0].strip()
        if not raw_id.isdigit():
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing ?telegram_id= (numeric Telegram user ID)")
            return

        days_raw = (query.get("days") or ["0"])[0].strip()
        try:
            days = int(days_raw) if days_raw.isdigit() else 0
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
