"""
Диагностика Premium: GET /api/premium_status?secret=SETUP_SECRET&telegram_id=ID
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
    """GET /api/premium_status?secret=...&telegram_id=123456789"""

    def do_GET(self) -> None:
        from api._setup_auth import verify_setup_secret

        if not verify_setup_secret(self):
            return

        query = parse_qs(urlparse(self.path).query)
        raw_id = (query.get("telegram_id") or [""])[0].strip()
        if not raw_id.isdigit():
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing ?telegram_id= (numeric Telegram user ID)")
            return

        try:
            from services.premium_grant import get_premium_status

            result = asyncio.run(get_premium_status(int(raw_id)))
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
