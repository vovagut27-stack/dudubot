"""AI-помощник для объяснения слов через Groq или xAI/Grok."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.error
import urllib.request

from services.word_service import WordEntry

logger = logging.getLogger(__name__)

AI_TIMEOUT_SECONDS = 25
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
XAI_URL = "https://api.x.ai/v1/chat/completions"


def ai_ready() -> bool:
    """True, если на Vercel/локально задан хотя бы один AI-ключ."""
    return bool(os.getenv("GROQ_API_KEY") or os.getenv("XAI_API_KEY"))


def _provider_config() -> tuple[str, str, str]:
    """Возвращает (provider, url, api_key)."""
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key:
        return "groq", GROQ_URL, groq_key

    xai_key = os.getenv("XAI_API_KEY", "").strip()
    if xai_key:
        return "xai", XAI_URL, xai_key

    raise RuntimeError("AI key is not configured")


def _model_for(provider: str) -> str:
    explicit = os.getenv("AI_MODEL", "").strip()
    if explicit:
        return explicit
    if provider == "xai":
        return os.getenv("XAI_MODEL", "grok-3-mini").strip()
    return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()


def _prompt(word: WordEntry, ui_language: str) -> str:
    examples = "\n".join(
        f"- {ex.text}" + (f" — {ex.translation}" if ex.translation else "")
        for ex in word.examples[:3]
    )
    return (
        "Ты дружелюбный преподаватель языков в Telegram-боте.\n"
        "Объясни слово коротко, понятно и полезно для запоминания.\n"
        f"Язык ответа интерфейса: {ui_language}.\n"
        f"Изучаемый язык: {word.language}.\n"
        f"Уровень: {word.level}.\n"
        f"Слово: {word.word}\n"
        f"Перевод: {word.translation}\n"
        f"Транскрипция: {word.transcription or '-'}\n"
        f"Часть речи: {word.part_of_speech or '-'}\n"
        f"Примеры из словаря:\n{examples or '-'}\n\n"
        "Формат ответа:\n"
        "1) Простое объяснение смысла.\n"
        "2) 2 коротких новых примера с переводом.\n"
        "3) Одна мнемоника/ассоциация.\n"
        "Не пиши длиннее 1200 символов. Можно использовать HTML-теги <b>, <i>."
    )


def _call_openai_compatible(url: str, api_key: str, model: str, prompt: str) -> str:
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Reply with concise educational content for a Telegram bot.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 650,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=AI_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"AI HTTP {exc.code}: {detail}") from exc

    data = json.loads(raw)
    return (data["choices"][0]["message"]["content"] or "").strip()


async def explain_word(word: WordEntry, *, ui_language: str = "ru") -> str:
    """Генерирует AI-разбор слова."""
    provider, url, api_key = _provider_config()
    model = _model_for(provider)
    prompt = _prompt(word, ui_language)
    logger.info("AI explain word=%s provider=%s model=%s", word.key, provider, model)
    return await asyncio.to_thread(_call_openai_compatible, url, api_key, model, prompt)
