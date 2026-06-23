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
    slot = notification_hour(user)
    if now_local.hour > slot:
        return True
    if now_local.hour == slot and now_local.minute >= 1:
        return True
    return False


def format_notification_slot(user: User) -> str:
    """Человекочитаемое время рассылки."""
    return user.notification_time.strftime("%H:%M")
