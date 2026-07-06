from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from handlers import daily
from models.models import WordStatus


class _FailingMessage:
    reply_markup = object()

    async def answer(self, *_args, **_kwargs):
        raise RuntimeError("telegram answer failed")

    async def edit_reply_markup(self, *_args, **_kwargs):
        raise RuntimeError("telegram markup failed")


class DailyWordCallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_dictionary_mark_survives_feedback_failures(self):
        calls = []

        class FakeUserService:
            def __init__(self, _session):
                pass

            async def get_by_telegram_id(self, telegram_id):
                return SimpleNamespace(id=1, telegram_id=telegram_id)

            def is_premium_active(self, _user):
                return True

            async def mark_word(self, _user, word_key, status, *, word_service):
                calls.append((word_key, status, word_service))
                return object(), "added"

        callback = SimpleNamespace(
            data="word:dict:en_a1_test",
            from_user=SimpleNamespace(id=12345),
            message=_FailingMessage(),
        )
        word_service = object()

        with (
            patch.object(daily, "UserService", FakeUserService),
            self.assertLogs("handlers.daily", level="ERROR"),
        ):
            await daily.word_add_dictionary(callback, object(), word_service)

        self.assertEqual(calls, [("en_a1_test", WordStatus.FAVORITE, word_service)])

    async def test_learned_mark_survives_feedback_failure(self):
        calls = []

        class FakeUserService:
            def __init__(self, _session):
                pass

            async def get_by_telegram_id(self, telegram_id):
                return SimpleNamespace(id=1, telegram_id=telegram_id)

            async def mark_word(self, _user, word_key, status, *, word_service):
                calls.append((word_key, status, word_service))
                return object(), "learned"

        class FakeWordService:
            def get_by_key(self, word_key):
                return SimpleNamespace(key=word_key)

        callback = SimpleNamespace(
            data="word:learned:en_a1_test",
            from_user=SimpleNamespace(id=12345),
            message=_FailingMessage(),
        )
        word_service = FakeWordService()

        with (
            patch.object(daily, "UserService", FakeUserService),
            self.assertLogs("handlers.daily", level="ERROR"),
        ):
            await daily.word_learned(callback, object(), word_service)

        self.assertEqual(calls, [("en_a1_test", WordStatus.LEARNED, word_service)])


if __name__ == "__main__":
    unittest.main()
