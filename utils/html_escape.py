"""HTML-экранирование для Telegram ParseMode.HTML."""

from __future__ import annotations

from html import escape


def h(text: str | None) -> str:
    """Безопасно вставляет пользовательский текст в HTML-сообщение."""
    return escape(text or "")
