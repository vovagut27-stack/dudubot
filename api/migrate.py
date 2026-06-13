"""
Ручной запуск миграций схемы: GET /api/migrate?secret=ВАШ_SETUP_SECRET
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def _run_migrate() -> dict:
    from bootstrap import ensure_database
    from config import get_settings
    from database import migrate_schema, turso_sync_engine, use_sync_sessions, engine

    settings = get_settings()
    await ensure_database(settings)

    applied: list[str] = []
    if use_sync_sessions and turso_sync_engine is not None:
        applied = await asyncio.to_thread(migrate_schema, turso_sync_engine)
    elif engine is not None:
        applied = await asyncio.to_thread(migrate_schema, engine)

    return {"ok": True, "applied": applied}


class handler(BaseHTTPRequestHandler):
    """GET /api/migrate?secret=ВАШ_SETUP_SECRET"""

    def do_GET(self) -> None:
        from urllib.parse import parse_qs, urlparse

        query = parse_qs(urlparse(self.path).query)
        secret = (query.get("secret") or [""])[0]
        expected = os.getenv("SETUP_SECRET", "")

        if not expected or secret != expected:
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Forbidden: wrong or missing ?secret=")
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
