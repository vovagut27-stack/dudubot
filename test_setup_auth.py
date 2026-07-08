import os
import unittest
from unittest.mock import patch

from utils.setup_auth import check_activation_code, check_premium_activation_code


class SetupAuthTests(unittest.TestCase):
    def test_setup_secret_is_not_a_bot_premium_activation_code(self) -> None:
        env = {
            **os.environ,
            "SETUP_SECRET": "setup-secret",
            "PREMIUM_ACTIVATION_CODE": "premium-code",
        }

        with patch.dict(os.environ, env, clear=True):
            self.assertFalse(check_activation_code("setup-secret"))
            self.assertFalse(check_premium_activation_code("setup-secret"))
            self.assertTrue(check_activation_code("premium-code"))
            self.assertTrue(check_premium_activation_code("premium-code"))


if __name__ == "__main__":
    unittest.main()
