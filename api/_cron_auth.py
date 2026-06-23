"""Проверка доступа к /api/cron/* (Vercel Cron, GitHub Actions, ручной вызов)."""

from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse


def _bearer_token(handler: BaseHTTPRequestHandler) -> str:
    auth = handler.headers.get("Authorization") or ""
    if auth.startswith("Bearer "):
        return auth[7:]
    return ""


def _matches_secret(token: str, *secrets: str) -> bool:
    return bool(token) and token in {s for s in secrets if s}


def _is_vercel_platform_cron(handler: BaseHTTPRequestHandler) -> bool:
    """Запрос от планировщика Vercel (User-Agent vercel-cron/1.0)."""
    if not os.getenv("VERCEL"):
        return False
    if not handler.headers.get("x-vercel-cron-schedule"):
        return False
    ua = (handler.headers.get("User-Agent") or "").lower()
    return "vercel-cron" in ua


def verify_cron_request(handler: BaseHTTPRequestHandler) -> bool:
    """
    Разрешает вызов если:
    - Vercel Cron: Bearer CRON_SECRET/SETUP_SECRET или platform cron без CRON_SECRET env
    - Authorization: Bearer CRON_SECRET или SETUP_SECRET
    - ?secret=CRON_SECRET или SETUP_SECRET
    - ALLOW_OPEN_CRON=true (только dev)
    """
    setup_secret = os.getenv("SETUP_SECRET", "")
    cron_secret_env = os.getenv("CRON_SECRET", "")
    cron_secret = cron_secret_env or setup_secret
    token = _bearer_token(handler)
    vercel_schedule = handler.headers.get("x-vercel-cron-schedule")

    if vercel_schedule:
        if _matches_secret(token, cron_secret, setup_secret):
            return True
        # Vercel шлёт Bearer только если задан CRON_SECRET; при одном SETUP_SECRET — только schedule + UA
        if not cron_secret_env and _is_vercel_platform_cron(handler):
            return True
        if cron_secret or setup_secret:
            return False
        return os.getenv("ALLOW_OPEN_CRON", "").lower() == "true"

    if _matches_secret(token, cron_secret, setup_secret):
        return True

    query = parse_qs(urlparse(handler.path).query)
    secret = (query.get("secret") or [""])[0]
    if _matches_secret(secret, cron_secret, setup_secret):
        return True

    return os.getenv("ALLOW_OPEN_CRON", "").lower() == "true"
