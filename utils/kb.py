"""
Lazy-импорт клавиатур — безопасно на Vercel (warm instances, циклические импорты).

Используйте: ``from utils.kb import premium_keyboard``
"""

from __future__ import annotations

from typing import Any

_cache: dict[str, Any] = {}


def __getattr__(name: str) -> Any:
    if not name.endswith("_keyboard"):
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    if name not in _cache:
        import utils.keyboards as keyboards

        _cache[name] = getattr(keyboards, name)
    return _cache[name]
