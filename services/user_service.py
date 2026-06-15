"""
Сервис пользователей: CRUD, геймификация, премиум.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import DAILY_WORDS_FREE_PER_LANGUAGE, DAILY_WORDS_PREMIUM
from models.models import (
    DailyWordLog,
    PaymentLog,
    User,
    UserWordProgress,
    WordStatus,
)
from services.word_service import WordService

logger = logging.getLogger(__name__)


class UserService:
    """Бизнес-логика работы с пользователями."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
    ) -> User:
        """Получает пользователя или создаёт нового."""
        result = await self._session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
            )
            self._session.add(user)
            await self._session.flush()
            logger.info("Новый пользователь: %s", telegram_id)
        else:
            user.username = username
            user.first_name = first_name
            user.last_active = datetime.now(timezone.utc).replace(tzinfo=None)

        return user

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Находит пользователя по Telegram ID."""
        result = await self._session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def complete_onboarding(
        self,
        user: User,
        level: str,
        languages: list[str],
        notification_time: time,
    ) -> None:
        """Завершает онбординг пользователя."""
        user.level = level
        user.languages = ",".join(languages)
        user.notification_time = notification_time
        user.onboarding_completed = True

    async def get_word_progress(
        self, user_id: int, word_key: str
    ) -> UserWordProgress | None:
        """Возвращает прогресс по слову."""
        result = await self._session.execute(
            select(UserWordProgress).where(
                UserWordProgress.user_id == user_id,
                UserWordProgress.word_key == word_key,
            )
        )
        return result.scalar_one_or_none()

    async def mark_word(
        self,
        user: User,
        word_key: str,
        status: WordStatus,
        *,
        word_service: WordService,
    ) -> tuple[int, str]:
        """
        Отмечает слово и начисляет очки.

        Returns: (начисленные очки, текст ответа)
        """
        progress = await self.get_word_progress(user.id, word_key)
        old_status = progress.status if progress else WordStatus.NEW.value

        if progress is None:
            progress = UserWordProgress(
                user_id=user.id,
                word_key=word_key,
                status=status.value,
                times_seen=1,
            )
            self._session.add(progress)
        else:
            progress.status = status.value
            progress.times_seen += 1

        points = 0
        message = ""

        if status == WordStatus.LEARNED:
            points = 15
            user.points += points
            if old_status != WordStatus.LEARNED.value:
                user.words_learned += 1
            self._update_streak(user)
            user.xp_level = word_service.calculate_level(user.points)
            message = f"🎉 Отлично! +{points} очков\n🔥 Streak: {user.streak} дней"
        elif status == WordStatus.UNKNOWN:
            points = 3
            user.points += points
            message = f"💪 Не сдавайся! +{points} очков за попытку"
        elif status == WordStatus.FAVORITE:
            message = "⭐ Слово добавлено в ваш словарь!"

        return points, message

    def _update_streak(self, user: User) -> None:
        """Обновляет серию дней обучения."""
        today = date.today()
        if user.last_word_date == today:
            return
        if user.last_word_date == today - timedelta(days=1):
            user.streak += 1
        else:
            user.streak = 1
        user.last_word_date = today
        user.best_streak = max(user.best_streak, user.streak)

    async def log_daily_word(
        self,
        user: User,
        word_key: str,
        language: str,
        sent_date: date,
        message_id: int | None = None,
    ) -> DailyWordLog | None:
        """Сохраняет отправленное слово дня."""
        result = await self._session.execute(
            select(DailyWordLog).where(
                DailyWordLog.user_id == user.id,
                DailyWordLog.sent_date == sent_date,
                DailyWordLog.word_key == word_key,
            )
        )
        log = result.scalar_one_or_none()
        if log is not None:
            log.message_id = message_id
            return log

        log = DailyWordLog(
            user_id=user.id,
            word_key=word_key,
            language=language,
            sent_date=sent_date,
            message_id=message_id,
        )
        self._session.add(log)
        return log

    def get_daily_word_limit(self, user: User) -> int:
        """Лимит слов в день: 3 на язык (Free) / 10 всего (Premium)."""
        if self.is_premium_active(user):
            return DAILY_WORDS_PREMIUM
        langs = user.language_list() or ["en"]
        return DAILY_WORDS_FREE_PER_LANGUAGE * len(langs)

    async def get_today_words(self, user: User, target_date: date | None = None) -> list[DailyWordLog]:
        """Возвращает слова, отправленные сегодня."""
        target_date = target_date or date.today()
        result = await self._session.execute(
            select(DailyWordLog).where(
                DailyWordLog.user_id == user.id,
                DailyWordLog.sent_date == target_date,
            )
        )
        return list(result.scalars().all())

    async def get_learned_words(self, user_id: int, limit: int = 50) -> list[UserWordProgress]:
        """Словарь выученных и избранных слов."""
        result = await self._session.execute(
            select(UserWordProgress)
            .where(
                UserWordProgress.user_id == user_id,
                UserWordProgress.status.in_(
                    [WordStatus.LEARNED.value, WordStatus.FAVORITE.value]
                ),
            )
            .order_by(UserWordProgress.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_onboarded_users(self) -> list[User]:
        """Все пользователи с завершённым онбордингом."""
        result = await self._session.execute(
            select(User).where(User.onboarding_completed.is_(True))
        )
        return list(result.scalars().all())

    async def get_users_for_notification(self, hour: int, minute: int) -> list[User]:
        """Пользователи, которым пора отправить слово в указанное время."""
        result = await self._session.execute(
            select(User).where(
                User.onboarding_completed.is_(True),
            )
        )
        users = list(result.scalars().all())
        return [
            u
            for u in users
            if u.notification_time.hour == hour and u.notification_time.minute == minute
        ]

    def is_premium_active(self, user: User) -> bool:
        """Проверяет активность премиум-подписки."""
        if not user.is_premium:
            return False
        if user.premium_until is None:
            return True
        until = user.premium_until
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        else:
            until = until.astimezone(timezone.utc)
        if until <= datetime.now(timezone.utc):
            user.is_premium = False
            return False
        return True

    async def activate_premium(
        self,
        user: User,
        charge_id: str,
        amount: int,
        payload: str,
        *,
        days: int = 30,
        is_subscription: bool = True,
    ) -> bool:
        """Активирует премиум после успешной оплаты Stars. Returns False если платёж уже обработан."""
        existing = await self._session.execute(
            select(PaymentLog).where(PaymentLog.charge_id == charge_id)
        )
        if existing.scalar_one_or_none() is not None:
            logger.info("Платёж %s уже обработан", charge_id)
            return False

        now = datetime.now(timezone.utc)
        base = user.premium_until if self.is_premium_active(user) and user.premium_until else now
        if base.tzinfo is None:
            base = base.replace(tzinfo=timezone.utc)

        user.is_premium = True
        user.premium_until = base + timedelta(days=days)
        user.last_payment_charge_id = charge_id

        payment = PaymentLog(
            user_id=user.id,
            charge_id=charge_id,
            amount=amount,
            payload=payload,
            is_subscription=is_subscription,
        )
        self._session.add(payment)
        logger.info("Premium активирован для user=%s до %s", user.telegram_id, user.premium_until)
        return True

    def grant_test_premium(self, user: User, *, days: int = 30) -> datetime:
        """Выдаёт Premium вручную (тест / админ), без записи в PaymentLog."""
        now = datetime.now(timezone.utc)
        base = now
        if self.is_premium_active(user) and user.premium_until:
            pu = user.premium_until
            if pu.tzinfo is None:
                pu = pu.replace(tzinfo=timezone.utc)
            else:
                pu = pu.astimezone(timezone.utc)
            base = pu

        user.is_premium = True
        user.premium_until = base + timedelta(days=days)
        logger.info(
            "Test Premium для user=%s до %s (+%d дн.)",
            user.telegram_id,
            user.premium_until,
            days,
        )
        return user.premium_until

    async def save_quiz_result(self, user_id: int, score: int, total: int) -> None:
        """Сохраняет результат квиза."""
        from models.models import QuizResult

        self._session.add(
            QuizResult(user_id=user_id, score=score, total=total)
        )
