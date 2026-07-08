import os
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import patch


_SETUP_AUTH_PATH = Path(__file__).resolve().parent / "utils" / "setup_auth.py"
_SPEC = spec_from_file_location("setup_auth_under_test", _SETUP_AUTH_PATH)
assert _SPEC is not None
assert _SPEC.loader is not None
setup_auth = module_from_spec(_SPEC)
_SPEC.loader.exec_module(setup_auth)


class SetupAuthTests(unittest.TestCase):
    def test_setup_secret_is_not_a_bot_premium_activation_code(self) -> None:
        env = {
            **os.environ,
            "SETUP_SECRET": "setup-secret",
            "PREMIUM_ACTIVATION_CODE": "premium-code",
        }

        with patch.dict(os.environ, env, clear=True):
            self.assertFalse(setup_auth.check_activation_code("setup-secret"))
            self.assertFalse(setup_auth.check_premium_activation_code("setup-secret"))
            self.assertTrue(setup_auth.check_activation_code("premium-code"))
            self.assertTrue(setup_auth.check_premium_activation_code("premium-code"))


if __name__ == "__main__":
    unittest.main()
