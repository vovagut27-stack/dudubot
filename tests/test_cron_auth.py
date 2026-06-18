import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from api._cron_auth import verify_cron_request


def make_handler(headers=None, path="/api/cron/daily"):
    return SimpleNamespace(headers=headers or {}, path=path)


class VerifyCronRequestTest(unittest.TestCase):
    def test_vercel_schedule_header_without_cron_secret_is_rejected(self):
        with patch.dict(os.environ, {}, clear=True):
            handler = make_handler({"x-vercel-cron-schedule": "0 4 * * *"})

            self.assertFalse(verify_cron_request(handler))

    def test_vercel_schedule_header_requires_matching_cron_secret(self):
        with patch.dict(os.environ, {"CRON_SECRET": "cron-secret"}, clear=True):
            self.assertFalse(
                verify_cron_request(
                    make_handler({"x-vercel-cron-schedule": "0 4 * * *"})
                )
            )
            self.assertFalse(
                verify_cron_request(
                    make_handler(
                        {
                            "x-vercel-cron-schedule": "0 4 * * *",
                            "Authorization": "Bearer wrong",
                        }
                    )
                )
            )
            self.assertTrue(
                verify_cron_request(
                    make_handler(
                        {
                            "x-vercel-cron-schedule": "0 4 * * *",
                            "Authorization": "Bearer cron-secret",
                        }
                    )
                )
            )

    def test_manual_bearer_setup_secret_still_works(self):
        with patch.dict(os.environ, {"SETUP_SECRET": "setup-secret"}, clear=True):
            handler = make_handler({"Authorization": "Bearer setup-secret"})

            self.assertTrue(verify_cron_request(handler))

    def test_open_cron_flag_still_allows_dev_calls(self):
        with patch.dict(os.environ, {"ALLOW_OPEN_CRON": "true"}, clear=True):
            self.assertTrue(verify_cron_request(make_handler()))


if __name__ == "__main__":
    unittest.main()
