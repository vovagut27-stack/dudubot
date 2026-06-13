"""
ORM-модели SQLAlchemy для бота «Слово Дня».
"""

from __future__ import annotations

from datetime import date, datetime, time
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Базовый класс для всех моделей."""


class WordStatus(StrEnum):
    """Статус слова у пользователя."""

    NEW = "new"
    LEARNED = "learned"
    UNKNOWN = "unknown"
    FAVORITE = "favorite"


class User(Base):
    """Пользователь Telegram."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Настройки обучения
    level: Mapped[str] = mapped_column(String(2), default="A1")
    # Языки через запятую: en,sr,ru
    languages: Mapped[str] = mapped_column(String(64), default="en")
    notification_time: Mapped[time] = mapped_column(Time, default=time(9, 0))
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/Moscow")

    # Геймификация
    points: Mapped[int] = mapped_column(Integer, default=0)
    streak: Mapped[int] = mapped_column(Integer, default=0)
    best_streak: Mapped[int] = mapped_column(Integer, default=0)
    xp_level: Mapped[int] = mapped_column(Integer, default=1)
    words_learned: Mapped[int] = mapped_column(Integer, default=0)

    # Онбординг и активность
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    last_word_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_active: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Премиум (Telegram Stars)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    premium_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_payment_charge_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    word_progress: Mapped[list["UserWordProgress"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    daily_words: Mapped[list["DailyWordLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def language_list(self) -> list[str]:
        """Возвращает список кодов языков пользователя."""
        return [lang.strip() for lang in self.languages.split(",") if lang.strip()]


class UserWordProgress(Base):
    """Прогресс пользователя по конкретному слову."""

    __tablename__ = "user_word_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "word_key", name="uq_user_word"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    word_key: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(16), default=WordStatus.NEW.value)
    times_seen: Mapped[int] = mapped_column(Integer, default=0)
    times_correct: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="word_progress")


class DailyWordLog(Base):
    """Лог ежедневных слов, отправленных пользователю."""

    __tablename__ = "daily_word_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "sent_date", "language", name="uq_daily_word"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    word_key: Mapped[str] = mapped_column(String(128))
    language: Mapped[str] = mapped_column(String(8))
    sent_date: Mapped[date] = mapped_column(Date)
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    user: Mapped["User"] = relationship(back_populates="daily_words")


class QuizResult(Base):
    """Результат прохождения мини-квиза."""

    __tablename__ = "quiz_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    score: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer, default=0)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PaymentLog(Base):
    """Журнал платежей Telegram Stars."""

    __tablename__ = "payment_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    charge_id: Mapped[str] = mapped_column(String(255), unique=True)
    amount: Mapped[int] = mapped_column(Integer)
    payload: Mapped[str] = mapped_column(String(128))
    is_subscription: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    raw_data: Mapped[str | None] = mapped_column(Text, nullable=True)
