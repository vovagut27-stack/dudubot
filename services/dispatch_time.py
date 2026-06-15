"""Логика времени автоматической рассылки слов дня."""

from __future__ import annotations

from datetime import datetime

from models.models import User


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
    return user.notification_time.hour == now_local.hour


def format_notification_slot(user: User) -> str:
    """Человекочитаемое время рассылки."""
    return user.notification_time.strftime("%H:%M")
