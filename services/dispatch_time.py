"""Логика времени автоматической рассылки слов дня."""

from __future__ import annotations

from datetime import datetime, time

from models.models import User


def notification_hour(user: User) -> int:
    """Час рассылки пользователя (устойчиво к строкам из SQLite/Turso)."""
    nt = user.notification_time
    if isinstance(nt, time):
        return nt.hour
    if isinstance(nt, str) and nt:
        return int(nt.split(":")[0])
    hour = getattr(nt, "hour", None)
    if hour is not None:
        return int(hour)
    return 9


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


def is_past_notification_today(user: User, now_local: datetime) -> bool:
    """True, если время рассылки сегодня уже наступило (для catch-up после cron)."""
    return now_local.hour >= notification_hour(user)


def format_notification_slot(user: User) -> str:
    """Человекочитаемое время рассылки."""
    hour = notification_hour(user)
    nt = user.notification_time
    if isinstance(nt, time):
        return nt.strftime("%H:%M")
    if isinstance(nt, str) and ":" in nt:
        parts = nt.split(":")
        return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    minute = getattr(nt, "minute", 0)
    return f"{hour:02d}:{int(minute):02d}"
