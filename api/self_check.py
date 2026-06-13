"""
Smoke-test всех keyboard-импортов. GET /api/self_check
"""

from __future__ import annotations

import asyncio
import json
import sys
import traceback
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), ".."))


def _check_imports() -> dict:
    errors: list[str] = []
    checks: dict[str, str] = {}

    keyboard_builders: dict[str, tuple] = {
        "main_menu_keyboard": ("ru",),
        "onboarding_level_keyboard": (),
        "onboarding_languages_keyboard": (set(),),
        "onboarding_time_keyboard": (),
        "settings_keyboard": ("ru",),
        "settings_level_keyboard": ("ru",),
        "settings_time_keyboard": ("ru",),
        "settings_languages_keyboard": (set(),),
        "settings_ui_language_keyboard": ("ru",),
        "word_actions_keyboard": ("test_word",),
        "quiz_answer_keyboard": ([("test:0", "A")],),
        "quiz_menu_keyboard": (),
        "premium_keyboard": ("ru",),
        "dictionary_keyboard": ([], 0, 1),
    }

    try:
        from utils import kb

        for name, args in keyboard_builders.items():
            fn = getattr(kb, name)
            if not callable(fn):
                checks[name] = "not callable"
                continue
            if name == "onboarding_languages_keyboard":
                fn(*args, ui_lang="ru")
            elif name == "settings_languages_keyboard":
                fn(*args, ui_lang="ru")
            elif name == "quiz_menu_keyboard":
                fn(is_premium=False)
            else:
                fn(*args)
            checks[name] = "ok"
    except Exception as exc:
        errors.append(f"kb import: {exc}")

    try:
        from bootstrap import get_application  # noqa: F401

        checks["bootstrap"] = "ok"
    except Exception as exc:
        errors.append(f"bootstrap: {exc}")

    return {"ok": not errors, "checks": checks, "errors": errors}


class handler(BaseHTTPRequestHandler):
    """GET /api/self_check"""

    def do_GET(self) -> None:
        try:
            result = _check_imports()
            body = json.dumps(result, ensure_ascii=False, indent=2)
            status = 200 if result.get("ok") else 500
        except Exception:
            body = json.dumps({"ok": False, "error": traceback.format_exc()}, ensure_ascii=False)
            status = 500

        self.send_response(status)
        self.send_header("Content-type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))
