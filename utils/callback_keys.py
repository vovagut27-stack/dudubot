"""Извлечение word_key из callback_data (ключи могут содержать подчёркивания)."""


def word_key_from_callback(data: str, prefix: str) -> str:
    """``word:learned:sr_a1_hello`` → ``sr_a1_hello``."""
    if not data.startswith(prefix):
        raise ValueError(f"Unexpected callback prefix: {data!r}")
    return data[len(prefix) :]
