"""
Диагностика: проверка env, webhook, бота. GET /api/health
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def _check() -> dict:
    result: dict = {
        "ok": True,
        "checks": {},
    }

    checks = result["checks"]
    checks["BOT_TOKEN"] = bool(os.getenv("BOT_TOKEN"))
    checks["BOT_USERNAME"] = os.getenv("BOT_USERNAME", "")
    checks["DATABASE_URL"] = bool(os.getenv("DATABASE_URL"))
    checks["TURSO_AUTH_TOKEN"] = bool(os.getenv("TURSO_AUTH_TOKEN"))
    checks["WEBHOOK_SECRET"] = bool(os.getenv("WEBHOOK_SECRET"))
    checks["SETUP_SECRET"] = bool(os.getenv("SETUP_SECRET"))

    production_url = (
        os.getenv("WEBHOOK_BASE_URL")
        or os.getenv("VERCEL_PROJECT_PRODUCTION_URL")
        or os.getenv("VERCEL_URL")
    )
    checks["production_url"] = production_url or "NOT SET"

    if not checks["BOT_TOKEN"]:
        result["ok"] = False
        result["hint"] = "Добавьте BOT_TOKEN в Vercel Environment Variables"
        return result

    if os.getenv("DATABASE_URL", "").startswith("libsql://") and not checks["TURSO_AUTH_TOKEN"]:
        result["ok"] = False
        result["hint"] = "Добавьте TURSO_AUTH_TOKEN для Turso"
        return result

    try:
        from aiogram import Bot

        bot = Bot(token=os.getenv("BOT_TOKEN", ""))
        me = await bot.get_me()
        checks["bot_name"] = me.username
        info = await bot.get_webhook_info()
        checks["webhook_url"] = info.url or "NOT SET — откройте /api/setup"
        checks["webhook_pending"] = info.pending_update_count
        if not info.url:
            result["ok"] = False
            result["hint"] = (
                f"Webhook не зарегистрирован! Откройте: "
                f"https://{production_url}/api/setup?secret=ВАШ_SETUP_SECRET"
            )
        await bot.session.close()
    except Exception as exc:
        result["ok"] = False
        result["hint"] = f"Ошибка Telegram API: {exc}"

    return result


class handler(BaseHTTPRequestHandler):
    """GET /api/health"""

    def do_GET(self) -> None:
        try:
            result = asyncio.run(_check())
            body = json.dumps(result, ensure_ascii=False, indent=2)
            status = 200 if result.get("ok") else 503
        except Exception as exc:
            body = json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False)
            status = 500

        self.send_response(status)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))
