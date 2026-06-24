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

TELEGRAM_CHECK_TIMEOUT = 10.0
AI_PROBE_TIMEOUT = 18.0


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
    checks["PREMIUM_ACTIVATION_CODE"] = bool(os.getenv("PREMIUM_ACTIVATION_CODE"))
    checks["CRON_SECRET"] = bool(os.getenv("CRON_SECRET"))
    checks["GROQ_API_KEY"] = bool(os.getenv("GROQ_API_KEY"))
    checks["XAI_API_KEY"] = bool(os.getenv("XAI_API_KEY"))
    checks["ai_ready"] = checks["GROQ_API_KEY"] or checks["XAI_API_KEY"]
    checks["ai_model"] = (
        os.getenv("AI_MODEL")
        or os.getenv("GROQ_MODEL")
        or os.getenv("XAI_MODEL")
        or "openai/gpt-oss-20b"
    )
    checks["cron_auth_ready"] = bool(
        os.getenv("CRON_SECRET") or os.getenv("SETUP_SECRET")
    )
    if not os.getenv("CRON_SECRET") and os.getenv("SETUP_SECRET"):
        checks["cron_hint"] = (
            "Для Vercel Cron задайте CRON_SECRET (= SETUP_SECRET) или используйте GitHub Actions hourly-dispatch"
        )
    checks["deploy_sha"] = os.getenv("VERCEL_GIT_COMMIT_SHA", "unknown")
    checks["dispatch_ready"] = bool(os.getenv("SETUP_SECRET") or os.getenv("CRON_SECRET"))

    production_url = (
        os.getenv("WEBHOOK_BASE_URL")
        or os.getenv("VERCEL_PROJECT_PRODUCTION_URL")
        or os.getenv("VERCEL_URL")
    )
    if production_url and not production_url.startswith("https://"):
        production_url = f"https://{production_url}"
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
        try:
            me = await asyncio.wait_for(bot.get_me(), timeout=TELEGRAM_CHECK_TIMEOUT)
            info = await asyncio.wait_for(
                bot.get_webhook_info(), timeout=TELEGRAM_CHECK_TIMEOUT
            )
        except asyncio.TimeoutError:
            result["ok"] = False
            result["hint"] = (
                f"Telegram API не ответил за {int(TELEGRAM_CHECK_TIMEOUT)}s — "
                "повторите /api/health позже"
            )
            await bot.session.close()
            return result

        checks["bot_name"] = me.username
        checks["webhook_url"] = info.url or "NOT SET — откройте /api/setup"
        checks["webhook_pending"] = info.pending_update_count
        expected_url = f"{production_url.rstrip('/')}/api/webhook" if production_url else ""
        if info.url and expected_url and info.url.rstrip("/") != expected_url.rstrip("/"):
            checks["webhook_url_mismatch"] = True
            result["ok"] = False
            result["hint"] = (
                f"Webhook указывает на {info.url}, ожидается {expected_url}. "
                f"Откройте {production_url}/api/setup?secret=ВАШ_SETUP_SECRET"
            )
        elif not info.url:
            result["ok"] = False
            result["hint"] = (
                f"Webhook не зарегистрирован! Откройте: "
                f"{production_url}/api/setup?secret=ВАШ_SETUP_SECRET"
            )
        elif info.pending_update_count:
            checks["webhook_hint"] = (
                f"В очереди {info.pending_update_count} update — "
                f"перерегистрируйте webhook: {production_url}/api/setup?secret=ВАШ_SETUP_SECRET"
            )
            if result.get("ok"):
                result["hint"] = checks["webhook_hint"]
        await bot.session.close()
    except Exception as exc:
        result["ok"] = False
        result["hint"] = f"Ошибка Telegram API: {exc}"

    if checks.get("ai_ready"):
        try:
            from services.ai_assistant import probe_ai_connection

            checks["ai_probe"] = await asyncio.wait_for(
                probe_ai_connection(), timeout=AI_PROBE_TIMEOUT
            )
            if not checks["ai_probe"].get("ok"):
                checks["ai_hint"] = (
                    "AI-ключ задан, но API не отвечает. "
                    "Проверьте GROQ_API_KEY или добавьте XAI_API_KEY как запасной."
                )
        except asyncio.TimeoutError:
            checks["ai_probe"] = {"ok": False, "error": "timeout"}
            checks["ai_hint"] = "AI probe timeout — провайдер не ответил вовремя"
        except Exception as exc:
            checks["ai_probe"] = {"ok": False, "error": str(exc)[:200]}

    if checks.get("cron_auth_ready"):
        base = checks.get("production_url", "").rstrip("/")
        checks["setup_url"] = f"{base}/api/setup?secret=SETUP_SECRET"
        checks["dispatch_test_url"] = f"{base}/api/migrate?secret=SETUP_SECRET&run_dispatch=1"
    else:
        checks["dispatch_hint"] = "Добавьте SETUP_SECRET на Vercel для cron и GitHub Actions"

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
