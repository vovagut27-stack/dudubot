import os
import unittest
from contextlib import asynccontextmanager
from unittest.mock import patch

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from models.models import Base, User
from services import premium_grant


class PremiumGrantUsernameLookupTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        await self.engine.dispose()

    async def _noop_ready(self, settings) -> None:
        return None

    @asynccontextmanager
    async def _session_scope(self):
        async with self.session_factory() as session:
            yield session
            await session.commit()

    async def _add_user(self, telegram_id: int, username: str) -> None:
        async with self.session_factory() as session:
            session.add(User(telegram_id=telegram_id, username=username))
            await session.commit()

    async def test_username_underscore_matches_literal_stored_username(self) -> None:
        await self._add_user(telegram_id=111, username="MillkaA2MKY")
        await self._add_user(telegram_id=222, username="Millka_2MKY")

        with (
            patch.object(premium_grant, "get_settings", lambda: object()),
            patch.object(premium_grant, "ensure_database_ready", self._noop_ready),
            patch.object(premium_grant, "session_scope", self._session_scope),
            patch.dict(os.environ, {"BOT_TOKEN": ""}),
        ):
            resolved = await premium_grant.resolve_telegram_id_by_username("Millka_2MKY")

        self.assertEqual(resolved, 222)

    async def test_username_underscore_does_not_match_neighbor_username(self) -> None:
        await self._add_user(telegram_id=111, username="MillkaA2MKY")

        with (
            patch.object(premium_grant, "get_settings", lambda: object()),
            patch.object(premium_grant, "ensure_database_ready", self._noop_ready),
            patch.object(premium_grant, "session_scope", self._session_scope),
            patch.dict(os.environ, {"BOT_TOKEN": ""}),
        ):
            resolved = await premium_grant.resolve_telegram_id_by_username("Millka_2MKY")

        self.assertIsNone(resolved)


if __name__ == "__main__":
    unittest.main()
