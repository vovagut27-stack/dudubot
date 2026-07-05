from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path
from unittest import IsolatedAsyncioTestCase

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from models.models import Base, DailyWordLog, User
from services.user_service import UserService


class _EmptyResult:
    def scalar_one_or_none(self):
        return None


class RaceBlindSession(AsyncSession):
    """Test session that can miss one daily-word lookup to mimic a write race."""

    force_missing_daily_word_lookup = False

    async def execute(self, statement, *args, **kwargs):
        if self.force_missing_daily_word_lookup:
            statement_text = str(statement)
            if "daily_word_logs" in statement_text and "word_key" in statement_text:
                self.force_missing_daily_word_lookup = False
                return _EmptyResult()
        return await super().execute(statement, *args, **kwargs)


class UserServiceDailyWordLogTests(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self.tmpdir.name) / "test.sqlite"
        self.engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.Session = async_sessionmaker(
            self.engine,
            class_=RaceBlindSession,
            expire_on_commit=False,
        )

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()
        self.tmpdir.cleanup()

    async def test_duplicate_log_race_keeps_previous_batch_logs(self) -> None:
        target_date = date(2026, 7, 5)
        telegram_id = 4242

        async with self.Session() as session:
            user = User(
                telegram_id=telegram_id,
                username="daily_user",
                first_name="Daily",
                languages="en",
                level="A1",
                onboarding_completed=True,
            )
            session.add(user)
            await session.flush()
            session.add(
                DailyWordLog(
                    user_id=user.id,
                    word_key="race-word",
                    language="en",
                    sent_date=target_date,
                    message_id=100,
                )
            )
            await session.commit()

        async with self.Session() as session:
            user = (
                await session.execute(select(User).where(User.telegram_id == telegram_id))
            ).scalar_one()
            service = UserService(session)

            await service.log_daily_word(
                user=user,
                word_key="first-word",
                language="en",
                sent_date=target_date,
                message_id=101,
            )

            session.force_missing_daily_word_lookup = True
            duplicate = await service.log_daily_word(
                user=user,
                word_key="race-word",
                language="en",
                sent_date=target_date,
                message_id=102,
            )

            self.assertIsNotNone(duplicate)
            await session.commit()

        async with self.Session() as session:
            rows = (
                await session.execute(
                    select(DailyWordLog).where(DailyWordLog.sent_date == target_date)
                )
            ).scalars().all()

        keys = sorted(row.word_key for row in rows)
        self.assertEqual(keys, ["first-word", "race-word"])

