"""
Ручной запуск миграций: GET /api/migrate?secret=SETUP_SECRET
Тест Premium: GET /api/migrate?secret=SETUP_SECRET&grant_premium=TELEGRAM_ID
Premium по @username: GET /api/migrate?secret=SETUP_SECRET&grant_premium_user=Millka_2MKY
Рассылка: GET /api/migrate?secret=SETUP_SECRET&run_dispatch=1
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def _run_dispatch() -> dict:
    import os

    from bootstrap import get_application
    from services.daily_dispatch import run_daily_dispatch

    bot, _, word_service, settings = await get_application()
    try:
        result = await run_daily_dispatch(bot, settings, word_service)
        result["deploy_sha"] = os.getenv("VERCEL_GIT_COMMIT_SHA", "unknown")
        return result
    finally:
        if os.getenv("VERCEL"):
            await bot.session.close()


async def _run_migrate() -> dict:
    from bootstrap import ensure_database
    from config import get_settings
    from database import prepare_schema, turso_sync_engine, use_sync_sessions, engine

    settings = get_settings()
    await ensure_database(settings)

    applied: list[str] = []
    if use_sync_sessions and turso_sync_engine is not None:
        applied = await asyncio.to_thread(prepare_schema, turso_sync_engine)
    elif engine is not None:
        applied = await asyncio.to_thread(prepare_schema, engine)

    return {
        "ok": True,
        "applied": applied,
        "deploy_sha": os.getenv("VERCEL_GIT_COMMIT_SHA", "unknown"),
    }


class handler(BaseHTTPRequestHandler):
    """GET /api/migrate?secret=ВАШ_SETUP_SECRET"""

    def do_GET(self) -> None:
        from urllib.parse import parse_qs, urlparse

        query = parse_qs(urlparse(self.path).query)
        from api._setup_auth import allowed_setup_secrets

        secret = (query.get("secret") or [""])[0]
        allowed = allowed_setup_secrets()

        if not allowed or secret not in allowed:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden: wrong or missing ?secret=")
            return

        grant_raw = (query.get("grant_premium") or query.get("telegram_id") or [""])[0].strip()
        grant_user = (query.get("grant_premium_user") or query.get("username") or [""])[0].strip()
        dispatch_raw = (query.get("run_dispatch") or [""])[0].strip().lower()
        if dispatch_raw in ("1", "true", "yes"):
            try:
                result = asyncio.run(_run_dispatch())
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
            return

        if grant_user:
            try:
                from services.premium_grant import grant_test_premium_by_username

                days_raw = (query.get("days") or ["365"])[0].strip()
                days = int(days_raw) if days_raw.isdigit() else 365
                result = asyncio.run(
                    grant_test_premium_by_username(
                        grant_user,
                        days=days if days > 0 else None,
                    )
                )
                result["deploy_sha"] = os.getenv("VERCEL_GIT_COMMIT_SHA", "unknown")
                body = json.dumps(result, ensure_ascii=False, indent=2)
                status = 200 if result.get("ok") else 404
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
            return

        if grant_raw.isdigit():
            try:
                from services.premium_grant import grant_test_premium_to

                days_raw = (query.get("days") or ["0"])[0].strip()
                days = int(days_raw) if days_raw.isdigit() else 0
                result = asyncio.run(
                    grant_test_premium_to(
                        int(grant_raw),
                        days=days if days > 0 else None,
                    )
                )
                result["deploy_sha"] = os.getenv("VERCEL_GIT_COMMIT_SHA", "unknown")
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
            return

        try:
            result = asyncio.run(_run_migrate())
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
