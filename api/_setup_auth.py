"""Проверка SETUP_SECRET для диагностических API."""

from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse


def verify_setup_secret(handler: BaseHTTPRequestHandler) -> bool:
    """Возвращает False и отвечает 403, если secret неверный."""
    query = parse_qs(urlparse(handler.path).query)
    secret = (query.get("secret") or [""])[0]
    expected = os.getenv("SETUP_SECRET", "")
    if not expected or secret != expected:
        handler.send_response(403)
        handler.end_headers()
        handler.wfile.write(b"Forbidden: wrong or missing ?secret=")
        return False
    return True
