"""Разбор callback_data с временем HH:MM."""


def parse_time_callback(callback_data: str, prefix: str) -> tuple[int, int, str]:
    """
    Извлекает часы и минуты из callback вида ``onboard:time:09:00``.

    Returns:
        (hours, minutes, time_str) — time_str в формате ``09:00``
    """
    if not callback_data.startswith(prefix):
        raise ValueError(f"Unexpected callback: {callback_data!r}")

    time_str = callback_data[len(prefix) :]
    parts = time_str.split(":")
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        raise ValueError(f"Invalid time in callback: {callback_data!r}")

    return int(parts[0]), int(parts[1]), time_str
