from __future__ import annotations

import importlib
import sys
import types
import unittest
from unittest.mock import patch


class FakeBot:
    instances: list["FakeBot"] = []

    def __init__(self, token: str) -> None:
        self.token = token
        self.session = types.SimpleNamespace(close=self.close)
        self.closed = False
        FakeBot.instances.append(self)

    async def close(self) -> None:
        self.closed = True


class FakeCallbackQuery:
    calls: list[dict] = []

    @classmethod
    def model_validate(cls, raw, *, context=None):
        cls.calls.append({"raw": raw, "context": context})
        callback = cls()
        callback.data = raw.get("data")
        callback.bot = context["bot"]
        return callback


async def fake_answer_callback(callback, text):
    fake_answer_callback.calls.append((callback, text))
    return True


fake_answer_callback.calls = []


class WebhookEarlyAckTest(unittest.IsolatedAsyncioTestCase):
    async def test_early_ack_attaches_bot_context_to_callback_query(self) -> None:
        fake_aiogram = types.ModuleType("aiogram")
        fake_aiogram.Bot = FakeBot
        fake_aiogram_types = types.ModuleType("aiogram.types")
        fake_aiogram_types.CallbackQuery = FakeCallbackQuery
        fake_aiogram_types.Update = type("Update", (), {})
        fake_callback_guard = types.ModuleType("utils.callback_guard")
        fake_callback_guard.answer_callback = fake_answer_callback

        with patch.dict(
            sys.modules,
            {
                "aiogram": fake_aiogram,
                "aiogram.types": fake_aiogram_types,
                "utils.callback_guard": fake_callback_guard,
            },
        ), patch.dict("os.environ", {"BOT_TOKEN": "token"}, clear=False):
            sys.modules.pop("api.webhook", None)
            webhook = importlib.import_module("api.webhook")
            await webhook._early_ack_callback(
                {
                    "callback_query": {
                        "id": "callback-id",
                        "from": {"id": 1, "is_bot": False, "first_name": "User"},
                        "chat_instance": "chat-instance",
                        "data": "word:ai:example",
                    }
                }
            )

        self.assertEqual(len(FakeCallbackQuery.calls), 1)
        context = FakeCallbackQuery.calls[0]["context"]
        self.assertIs(context["bot"], FakeBot.instances[0])
        self.assertEqual(fake_answer_callback.calls[0][1], "Готовлю AI-разбор...")
        self.assertTrue(FakeBot.instances[0].closed)


if __name__ == "__main__":
    unittest.main()
