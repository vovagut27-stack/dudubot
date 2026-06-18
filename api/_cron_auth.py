"""Проверка доступа к /api/cron/* (Vercel Cron, GitHub Actions, ручной вызов)."""

from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse


def verify_cron_request(handler: BaseHTTPRequestHandler) -> bool:
    """
    Разрешает вызов если:
    - Vercel Cron (заголовок x-vercel-cron-schedule + Bearer CRON_SECRET)
    - Authorization: Bearer CRON_SECRET или SETUP_SECRET
    - ?secret=CRON_SECRET или SETUP_SECRET (внешний cron-job.org / GitHub Actions)
    - ALLOW_OPEN_CRON=true (только dev)
    """
    cron_secret = os.getenv("CRON_SECRET", "")
    setup_secret = os.getenv("SETUP_SECRET", "")
    vercel_schedule = handler.headers.get("x-vercel-cron-schedule")

    if vercel_schedule:
        auth = handler.headers.get("Authorization", "")
        return bool(cron_secret) and auth == f"Bearer {cron_secret}"

    auth = handler.headers.get("Authorization") or ""
    if auth.startswith("Bearer "):
        token = auth[7:]
        if cron_secret and token == cron_secret:
            return True
        if setup_secret and token == setup_secret:
            return True

    query = parse_qs(urlparse(handler.path).query)
    secret = (query.get("secret") or [""])[0]
    if cron_secret and secret == cron_secret:
        return True
    if setup_secret and secret == setup_secret:
        return True

    return os.getenv("ALLOW_OPEN_CRON", "").lower() == "true"
