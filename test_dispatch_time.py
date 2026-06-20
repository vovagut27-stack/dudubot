from datetime import datetime
import unittest

from models.models import User
from services.dispatch_time import (
    format_notification_slot,
    is_notification_hour,
    notification_time_parts,
)


class DispatchTimeTest(unittest.TestCase):
    def test_string_notification_time_is_formatted_and_matched(self) -> None:
        user = User(telegram_id=1)
        user.notification_time = "09:00:00"

        self.assertEqual(notification_time_parts(user), (9, 0))
        self.assertEqual(format_notification_slot(user), "09:00")
        self.assertTrue(is_notification_hour(user, datetime(2026, 6, 20, 9, 15)))

    def test_unpadded_string_notification_time_is_supported(self) -> None:
        user = User(telegram_id=2)
        user.notification_time = "7:30"

        self.assertEqual(notification_time_parts(user), (7, 30))
        self.assertEqual(format_notification_slot(user), "07:30")

    def test_invalid_notification_time_falls_back_to_default_slot(self) -> None:
        user = User(telegram_id=3)
        user.notification_time = "not-a-time"

        self.assertEqual(notification_time_parts(user), (9, 0))
        self.assertEqual(format_notification_slot(user), "09:00")


if __name__ == "__main__":
    unittest.main()
