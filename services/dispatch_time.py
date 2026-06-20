"""Логика времени автоматической рассылки слов дня."""

from __future__ import annotations

from datetime import datetime, time

from models.models import User


def _coerce_notification_time(value: object) -> time:
    """Notification time normalized from SQLAlchemy/libSQL return values."""
    if isinstance(value, time):
        return value
    if isinstance(value, str) and value:
        try:
            return time.fromisoformat(value)
        except ValueError:
            parts = value.split(":")
            try:
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
                return time(hour, minute)
            except (TypeError, ValueError):
                pass
    hour = getattr(value, "hour", None)
    minute = getattr(value, "minute", 0)
    if hour is not None:
        try:
            return time(int(hour), int(minute or 0))
        except (TypeError, ValueError):
            pass
    return time(9, 0)


def notification_time_parts(user: User) -> tuple[int, int]:
    """Hour/minute for dispatch comparisons, tolerant of SQLite/Turso strings."""
    nt = _coerce_notification_time(user.notification_time)
    return nt.hour, nt.minute


def notification_hour(user: User) -> int:
    """Час рассылки пользователя (устойчиво к строкам из SQLite/Turso)."""
    return notification_time_parts(user)[0]


def user_local_now(user: User, default_tz: str) -> datetime:
    """Текущее локальное время пользователя."""
    from zoneinfo import ZoneInfo

    try:
        tz = ZoneInfo(user.timezone or default_tz)
    except Exception:
        tz = ZoneInfo(default_tz)
    return datetime.now(tz)


def is_notification_hour(user: User, now_local: datetime) -> bool:
    """
    True, если сейчас час ежедневной рассылки пользователя.

    Слоты: 07:00, 08:00, 09:00… — сравниваем только час.
    Повторная отправка в тот же день блокируется логом daily_word_logs.
    """
    return notification_hour(user) == now_local.hour


def format_notification_slot(user: User) -> str:
    """Человекочитаемое время рассылки."""
    return _coerce_notification_time(user.notification_time).strftime("%H:%M")
