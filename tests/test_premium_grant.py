from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from models.models import User
from services.user_service import UserService


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _ExistingUserSession:
    def __init__(self, user: User):
        self.user = user

    async def execute(self, _statement):
        return _ScalarResult(self.user)


class _FakeBot:
    def __init__(self, token: str):
        self.token = token
        self.session = SimpleNamespace(close=AsyncMock())

    async def get_chat(self, username: str):
        self.requested_username = username
        return SimpleNamespace(id=987654321, type="private")


class PremiumGrantTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_or_create_preserves_existing_profile_on_id_only_lookup(self):
        user = User(telegram_id=123, username="alice", first_name="Alice")
        service = UserService(_ExistingUserSession(user))

        result = await service.get_or_create(telegram_id=123)

        self.assertIs(result, user)
        self.assertEqual(user.username, "alice")
        self.assertEqual(user.first_name, "Alice")
        self.assertIsNotNone(user.last_active)

    async def test_get_or_create_updates_profile_when_values_are_present(self):
        user = User(telegram_id=123, username="alice", first_name="Alice")
        service = UserService(_ExistingUserSession(user))

        await service.get_or_create(
            telegram_id=123,
            username="bob",
            first_name="Bob",
        )

        self.assertEqual(user.username, "bob")
        self.assertEqual(user.first_name, "Bob")

    async def test_username_resolution_uses_live_private_chat(self):
        from services import premium_grant

        with (
            patch.object(premium_grant, "get_settings", return_value=object()),
            patch.object(premium_grant, "ensure_database_ready", AsyncMock()),
            patch.object(premium_grant.os, "getenv", return_value="token"),
            patch("aiogram.Bot", _FakeBot),
        ):
            telegram_id = await premium_grant.resolve_telegram_id_by_username(
                "@alice"
            )

        self.assertEqual(telegram_id, 987654321)


if __name__ == "__main__":
    unittest.main()
