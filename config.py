"""
Конфигурация бота «Слово Дня».

Все настройки загружаются из переменных окружения (.env).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Корневая директория проекта
BASE_DIR = Path(__file__).resolve().parent

# Загружаем .env из корня проекта
load_dotenv(BASE_DIR / ".env")

# Поддерживаемые языки: код -> отображаемое имя
SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "🇬🇧 English",
    "sr": "🇷🇸 Српски",
    "ru": "🇷🇺 Русский",
    "be": "🇧🇾 Беларуская",
}

# Уровни CEFR
CEFR_LEVELS: tuple[str, ...] = ("A1", "A2", "B1", "B2", "C1", "C2")

# Время подписки Telegram Stars (30 дней в секундах — требование Bot API)
STAR_SUBSCRIPTION_PERIOD = 2_592_000

# Ссылка на поддержку проекта
SUPPORT_URL = "https://donatty.com/creator_bots"


def normalize_database_url(url: str) -> str:
    """
    Приводит URL БД к async-формату для SQLAlchemy.

    Neon/Vercel Postgres часто выдают postgres:// — конвертируем в postgresql+asyncpg://
    """
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


@dataclass(frozen=True, slots=True)
class Settings:
    """Неизменяемый объект настроек приложения."""

    bot_token: str
    database_url: str
    log_level: str
    timezone: str
    premium_stars_price: int
    words_file: Path
    admin_ids: tuple[int, ...] = field(default_factory=tuple)

    @classmethod
    def from_env(cls) -> "Settings":
        """Создаёт настройки из переменных окружения."""
        admin_raw = os.getenv("ADMIN_IDS", "")
        admin_ids = tuple(
            int(x.strip()) for x in admin_raw.split(",") if x.strip().isdigit()
        )

        db_url = os.getenv(
            "DATABASE_URL",
            f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'bot.db'}",
        )

        return cls(
            bot_token=os.getenv("BOT_TOKEN", ""),
            database_url=normalize_database_url(db_url),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            timezone=os.getenv("TIMEZONE", "Europe/Moscow"),
            premium_stars_price=int(os.getenv("PREMIUM_STARS_PRICE", "150")),
            words_file=BASE_DIR / "data" / "words.json",
            admin_ids=admin_ids,
        )

    def validate(self) -> None:
        """Проверяет обязательные параметры перед запуском."""
        if not self.bot_token:
            raise ValueError(
                "BOT_TOKEN не задан. Скопируйте .env.example в .env и укажите токен."
            )


def get_settings() -> Settings:
    """Возвращает проверенный объект настроек."""
    settings = Settings.from_env()
    settings.validate()
    return settings
