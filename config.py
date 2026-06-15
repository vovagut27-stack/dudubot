"""
Конфигурация бота «Слово Дня».

Все настройки загружаются из переменных окружения (.env).
"""

from __future__ import annotations

import functools
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Корневая директория проекта
BASE_DIR = Path(__file__).resolve().parent

# Загружаем .env из корня проекта
load_dotenv(BASE_DIR / ".env")

# Языки для изучения: код -> отображаемое имя
SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "🇬🇧 English",
    "de": "🇩🇪 Deutsch",
    "it": "🇮🇹 Italiano",
    "sr": "🇷🇸 Српски",
    "ru": "🇷🇺 Русский",
    "be": "🇧🇾 Беларуская",
}

# Языки интерфейса бота
UI_LANGUAGES: dict[str, str] = {
    "ru": "🇷🇺 Русский",
    "en": "🇬🇧 English",
    "de": "🇩🇪 Deutsch",
    "it": "🇮🇹 Italiano",
}

# Уровни CEFR
CEFR_LEVELS: tuple[str, ...] = ("A1", "A2", "B1", "B2", "C1", "C2")

# Допустимое время уведомлений (HH:MM)
NOTIFICATION_TIMES: frozenset[str] = frozenset(
    {"07:00", "08:00", "09:00", "12:00", "18:00", "20:00", "21:00"}
)

# Время подписки Telegram Stars (30 дней в секундах — требование Bot API)
STAR_SUBSCRIPTION_PERIOD = 2_592_000

# Ссылка на поддержку проекта
SUPPORT_URL = "https://donatty.com/creator_bots"

# Слов в день: бесплатно — на каждый язык / Premium — всего
DAILY_WORDS_FREE_PER_LANGUAGE = 3
DAILY_WORDS_PREMIUM = 10

# Квизы
QUIZ_SIZE_BASIC = 5
QUIZ_SIZE_EXTENDED = 10
QUIZ_SIZE_REVERSE = 7
QUIZ_SIZE_MULTILANG = 10
QUIZ_POINTS_BASIC = 10
QUIZ_POINTS_PREMIUM = 15

# Код верификации в каталоге @appss (/appss_verify)
APPSS_VERIFY_CODE = os.getenv("APPSS_VERIFY_CODE", "appss_8db7f6")


def normalize_database_url(url: str) -> str:
    """
    Приводит URL БД к формату для SQLAlchemy.

    - postgres:// → postgresql+asyncpg://
    - libsql:// — без изменений (Turso)
    """
    if url.startswith("libsql://"):
        return url
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
    database_auth_token: str | None
    turso_embedded_path: Path
    log_level: str
    timezone: str
    premium_stars_price: int
    words_file: Path
    admin_ids: tuple[int, ...] = field(default_factory=tuple)

    def is_turso(self) -> bool:
        """True, если используется Turso (libsql://)."""
        return self.database_url.startswith("libsql://")

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

        auth_token = (
            os.getenv("TURSO_AUTH_TOKEN")
            or os.getenv("DATABASE_AUTH_TOKEN")
            or None
        )

        default_embedded = (
            Path("/tmp/turso_bot.db")
            if os.getenv("VERCEL")
            else BASE_DIR / "data" / "embedded.db"
        )
        embedded = Path(os.getenv("TURSO_EMBEDDED_PATH", str(default_embedded)))

        return cls(
            bot_token=os.getenv("BOT_TOKEN", ""),
            database_url=normalize_database_url(db_url),
            database_auth_token=auth_token,
            turso_embedded_path=embedded,
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
        if self.is_turso() and not self.database_auth_token:
            raise ValueError(
                "Для Turso (libsql://) нужен TURSO_AUTH_TOKEN. "
                "Получите: turso db tokens create <имя-базы> — или в Turso Dashboard."
            )


def get_settings() -> Settings:
    """Возвращает проверенный объект настроек (кэш на время жизни процесса)."""
    return _cached_settings()


@functools.lru_cache(maxsize=1)
def _cached_settings() -> Settings:
    settings = Settings.from_env()
    settings.validate()
    return settings
