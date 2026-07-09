from __future__ import annotations

import unittest
from unittest.mock import patch

from api import _setup_auth
from api.migrate import _is_dispatch_request


class _DummyHandler:
    def __init__(self, path: str) -> None:
        self.path = path
        self.status: int | None = None
        self.body = bytearray()

    def send_response(self, status: int) -> None:
        self.status = status

    def end_headers(self) -> None:
        pass

    @property
    def wfile(self):
        return self

    def write(self, data: bytes) -> None:
        self.body.extend(data)


class SetupAuthTests(unittest.TestCase):
    def test_setup_auth_uses_only_setup_secret(self) -> None:
        with patch.dict(
            "os.environ",
            {"SETUP_SECRET": "setup-secret", "CRON_SECRET": "cron-secret"},
            clear=True,
        ):
            self.assertEqual(_setup_auth.allowed_setup_secrets(), {"setup-secret"})

    def test_cron_secret_does_not_authorize_setup_api(self) -> None:
        handler = _DummyHandler("/api/setup?secret=cron-secret")

        with patch.dict(
            "os.environ",
            {"SETUP_SECRET": "setup-secret", "CRON_SECRET": "cron-secret"},
            clear=True,
        ):
            self.assertFalse(_setup_auth.verify_setup_secret(handler))

        self.assertEqual(handler.status, 403)
        self.assertIn(b"Forbidden", handler.body)

    def test_setup_secret_authorizes_setup_api(self) -> None:
        handler = _DummyHandler("/api/setup?secret=setup-secret")

        with patch.dict(
            "os.environ",
            {"SETUP_SECRET": "setup-secret", "CRON_SECRET": "cron-secret"},
            clear=True,
        ):
            self.assertTrue(_setup_auth.verify_setup_secret(handler))

        self.assertIsNone(handler.status)
        self.assertEqual(handler.body, bytearray())


class MigrateDispatchRequestTests(unittest.TestCase):
    def test_dispatch_request_accepts_true_values(self) -> None:
        for value in ("1", "true", "yes", " TRUE "):
            with self.subTest(value=value):
                self.assertTrue(_is_dispatch_request({"run_dispatch": [value]}))

    def test_dispatch_request_rejects_absent_or_false_values(self) -> None:
        for query in ({}, {"run_dispatch": ["0"]}, {"run_dispatch": ["false"]}):
            with self.subTest(query=query):
                self.assertFalse(_is_dispatch_request(query))


if __name__ == "__main__":
    unittest.main()
