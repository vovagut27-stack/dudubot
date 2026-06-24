"""AI-помощник для объяснения слов через Groq или xAI/Grok."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import aiohttp

from services.word_service import WordEntry

logger = logging.getLogger(__name__)

AI_TIMEOUT_SECONDS = 15
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
XAI_URL = "https://api.x.ai/v1/chat/completions"
GROQ_FALLBACK_MODELS = (
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
)
XAI_FALLBACK_MODELS = (
    "grok-3-mini",
    "grok-4-fast",
)
_HTTP_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "DuduDayBot/1.0 (+https://dudubot-ten.vercel.app)",
}


def ai_ready() -> bool:
    """True, если на Vercel/локально задан хотя бы один AI-ключ."""
    return bool(os.getenv("GROQ_API_KEY") or os.getenv("XAI_API_KEY"))


def _all_providers() -> list[tuple[str, str, str]]:
    """Все настроенные провайдеры (Groq приоритетнее xAI)."""
    providers: list[tuple[str, str, str]] = []
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key:
        providers.append(("groq", GROQ_URL, groq_key))
    xai_key = os.getenv("XAI_API_KEY", "").strip()
    if xai_key:
        providers.append(("xai", XAI_URL, xai_key))
    if not providers:
        raise RuntimeError("AI key is not configured")
    return providers


def _models_for(provider: str) -> list[str]:
    explicit = os.getenv("AI_MODEL", "").strip()
    if explicit:
        return [explicit]
    if provider == "xai":
        configured = os.getenv("XAI_MODEL", "").strip()
        return [configured] if configured else list(XAI_FALLBACK_MODELS)
    configured = os.getenv("GROQ_MODEL", "").strip()
    return [configured] if configured else list(GROQ_FALLBACK_MODELS)


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


def _is_provider_block_error(exc: Exception) -> bool:
    """403/401/1010 — провайдер недоступен, пробуем следующий."""
    text = str(exc).lower()
    return any(token in text for token in ("403", "401", "1010", "forbidden"))


async def _call_openai_compatible(
    session: aiohttp.ClientSession,
    url: str,
    api_key: str,
    model: str,
    prompt: str,
) -> str:
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
    headers = {**_HTTP_HEADERS, "Authorization": f"Bearer {api_key}"}
    async with session.post(url, json=payload, headers=headers) as response:
        raw = await response.text()
        if response.status >= 400:
            raise RuntimeError(f"AI HTTP {response.status}: {raw[:500]}")
        data = json.loads(raw)
        return (data["choices"][0]["message"]["content"] or "").strip()


def fallback_explanation(word: WordEntry) -> str:
    """Локальный разбор, если AI API временно недоступен."""
    examples = "\n".join(
        f"- {ex.text}" + (f" — {ex.translation}" if ex.translation else "")
        for ex in word.examples[:2]
    )
    parts = [
        f"{word.word} — {word.translation}",
        f"Уровень: {word.level}",
    ]
    if word.transcription:
        parts.append(f"Транскрипция: {word.transcription}")
    if word.part_of_speech:
        parts.append(f"Часть речи: {word.part_of_speech}")
    if examples:
        parts.append(f"\nПримеры:\n{examples}")
    parts.append("\nAI временно недоступен, но словарный разбор уже можно использовать.")
    return "\n".join(parts)


async def explain_word(word: WordEntry, *, ui_language: str = "ru") -> str:
    """Генерирует AI-разбор слова."""
    prompt = _prompt(word, ui_language)
    last_error: Exception | None = None
    timeout = aiohttp.ClientTimeout(total=AI_TIMEOUT_SECONDS)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for provider, url, api_key in _all_providers():
            provider_blocked = False
            for model in _models_for(provider):
                logger.info(
                    "AI explain word=%s provider=%s model=%s",
                    word.key,
                    provider,
                    model,
                )
                try:
                    result = await _call_openai_compatible(
                        session, url, api_key, model, prompt
                    )
                    if result:
                        return result
                except Exception as exc:
                    last_error = exc
                    logger.warning(
                        "AI model failed word=%s provider=%s model=%s error=%s",
                        word.key,
                        provider,
                        model,
                        exc,
                    )
                    if _is_provider_block_error(exc):
                        provider_blocked = True
                        break
            if provider_blocked:
                continue
    raise RuntimeError(f"All AI models failed: {last_error}") from last_error


async def probe_ai_connection() -> dict[str, Any]:
    """Быстрая проверка доступности AI API (для /api/health)."""
    prompt = 'Reply with exactly one word: OK'
    timeout = aiohttp.ClientTimeout(total=AI_TIMEOUT_SECONDS)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        for provider, url, api_key in _all_providers():
            for model in _models_for(provider)[:1]:
                try:
                    result = await _call_openai_compatible(
                        session, url, api_key, model, prompt
                    )
                    return {
                        "ok": True,
                        "provider": provider,
                        "model": model,
                        "sample": (result or "")[:40],
                    }
                except Exception as exc:
                    if _is_provider_block_error(exc):
                        break
                    return {"ok": False, "provider": provider, "model": model, "error": str(exc)[:200]}
    return {"ok": False, "error": "all providers failed"}
