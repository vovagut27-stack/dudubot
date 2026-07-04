from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from handlers.start import _show_onboarding_done


class _FailingMessage:
    async def edit_text(self, *_args, **_kwargs):
        raise RuntimeError("edit failed")

    async def answer(self, *_args, **_kwargs):
        raise RuntimeError("send failed")


class OnboardingTests(unittest.IsolatedAsyncioTestCase):
    async def test_show_onboarding_done_swallows_telegram_ui_failures(self):
        callback = SimpleNamespace(
            from_user=SimpleNamespace(id=123),
            answer=AsyncMock(return_value=None),
            data="onboard:time:09:00",
        )

        with self.assertLogs("handlers.start", level="ERROR"):
            await _show_onboarding_done(
                callback,
                _FailingMessage(),
                "ru",
                level="A1",
                langs="English",
                time_str="09:00",
            )

        callback.answer.assert_awaited_once_with("🚀", show_alert=False)


if __name__ == "__main__":
    unittest.main()
