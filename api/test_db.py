"""
Диагностика БД + выдача Premium на Vercel.

GET /api/test_db?secret=SETUP_SECRET
GET /api/test_db?secret=SETUP_SECRET&grant_premium=TELEGRAM_ID
GET /api/test_db?secret=SETUP_SECRET&premium_status=TELEGRAM_ID
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


async def _test_db(telegram_id: int | None = None) -> dict:
    from bootstrap import ensure_database
    from config import get_settings
    from database import session_scope
    from services.user_service import UserService

    settings = get_settings()
    await ensure_database(settings)

    tid = telegram_id or 999888777
    async with session_scope() as session:
        svc = UserService(session)
        user = await svc.get_or_create(
            telegram_id=tid,
            username="test_user",
            first_name="Test",
        )
        return {
            "ok": True,
            "deploy_sha": os.getenv("VERCEL_GIT_COMMIT_SHA", "local"),
            "user_telegram_id": user.telegram_id,
            "onboarding": user.onboarding_completed,
            "is_premium": svc.is_premium_active(user),
            "premium_until": user.premium_until.isoformat() if user.premium_until else None,
        }


class handler(BaseHTTPRequestHandler):
    """GET /api/test_db?secret=SETUP_SECRET"""

    def do_GET(self) -> None:
        from api._setup_auth import verify_setup_secret

        if not verify_setup_secret(self):
            return

        query = parse_qs(urlparse(self.path).query)
        grant_raw = (query.get("grant_premium") or [""])[0].strip()
        status_raw = (query.get("premium_status") or [""])[0].strip()

        try:
            if grant_raw.isdigit():
                from services.premium_grant import grant_test_premium_to

                days_raw = (query.get("days") or ["0"])[0].strip()
                days = int(days_raw) if days_raw.isdigit() else 0
                result = asyncio.run(
                    grant_test_premium_to(
                        int(grant_raw),
                        days=days if days > 0 else None,
                    )
                )
            elif status_raw.isdigit():
                from services.premium_grant import get_premium_status

                result = asyncio.run(get_premium_status(int(status_raw)))
            else:
                tid_raw = (query.get("telegram_id") or [""])[0].strip()
                tid = int(tid_raw) if tid_raw.isdigit() else None
                result = asyncio.run(_test_db(tid))
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
