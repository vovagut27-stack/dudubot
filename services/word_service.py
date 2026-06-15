"""
Сервис работы со словами: загрузка, выбор слова дня, форматирование.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from config import CEFR_LEVELS, SUPPORTED_LANGUAGES
from utils.html_escape import h

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ExampleEntry:
    """Пример предложения с переводом."""

    text: str
    translation: str


@dataclass(frozen=True, slots=True)
class WordEntry:
    """Структура одного слова из словаря."""

    key: str
    language: str
    level: str
    word: str
    translation: str
    transcription: str
    part_of_speech: str
    examples: list[ExampleEntry]

    @classmethod
    def from_dict(cls, data: dict) -> "WordEntry":
        examples: list[ExampleEntry] = []
        for item in data.get("examples", []):
            if isinstance(item, str):
                examples.append(ExampleEntry(text=item, translation=""))
            else:
                examples.append(
                    ExampleEntry(
                        text=item["text"],
                        translation=item.get("translation", ""),
                    )
                )
        return cls(
            key=data["key"],
            language=data["language"],
            level=data["level"],
            word=data["word"],
            translation=data["translation"],
            transcription=data.get("transcription", ""),
            part_of_speech=data.get("part_of_speech", ""),
            examples=examples,
        )


class WordService:
    """Загружает слова из JSON и выбирает слова дня."""

    def __init__(self, words_file: Path) -> None:
        self._words_file = words_file
        self._words: list[WordEntry] = []
        self._by_key: dict[str, WordEntry] = {}
        self._by_lang_level: dict[tuple[str, str], list[WordEntry]] = {}
        self.reload()

    def reload(self) -> None:
        """Перезагружает словарь из файла."""
        try:
            with self._words_file.open(encoding="utf-8") as f:
                raw = json.load(f)
            self._words = [WordEntry.from_dict(w) for w in raw.get("words", [])]
            self._rebuild_indexes()
            logger.info("Загружено %d слов из %s", len(self._words), self._words_file)
        except FileNotFoundError:
            logger.error("Файл слов не найден: %s", self._words_file)
            self._words = []
            self._by_key = {}
            self._by_lang_level = {}
        except json.JSONDecodeError as exc:
            logger.exception("Ошибка парсинга words.json: %s", exc)
            self._words = []
            self._by_key = {}
            self._by_lang_level = {}

    def _rebuild_indexes(self) -> None:
        by_key: dict[str, WordEntry] = {}
        by_lang_level: dict[tuple[str, str], list[WordEntry]] = {}
        for word in self._words:
            by_key[word.key] = word
            bucket = by_lang_level.setdefault((word.language, word.level), [])
            bucket.append(word)
        self._by_key = by_key
        self._by_lang_level = by_lang_level

    def get_by_key(self, word_key: str) -> WordEntry | None:
        """Находит слово по уникальному ключу."""
        return self._by_key.get(word_key)

    def filter_words(
        self,
        language: str,
        level: str,
        *,
        max_level: bool = True,
    ) -> list[WordEntry]:
        """
        Фильтрует слова по языку и уровню.

        max_level=True — включает слова текущего и более низких уровней.
        """
        if max_level:
            level_idx = CEFR_LEVELS.index(level) if level in CEFR_LEVELS else 0
            allowed_levels = CEFR_LEVELS[: level_idx + 1]
        else:
            allowed_levels = (level,)

        result: list[WordEntry] = []
        for lvl in allowed_levels:
            result.extend(self._by_lang_level.get((language, lvl), []))
        return result

    def pick_daily_word(
        self,
        language: str,
        level: str,
        target_date: date | None = None,
        user_id: int | None = None,
        slot: int = 0,
    ) -> WordEntry | None:
        """
        Детерминированно выбирает одно слово.

        slot — порядковый номер слова за день (0, 1, 2…).
        """
        candidates = self.filter_words(language, level, max_level=False)
        if not candidates:
            return None

        target_date = target_date or date.today()
        seed = f"{target_date.isoformat()}:{language}:{user_id or 0}:{slot}"
        digest = hashlib.sha256(seed.encode()).hexdigest()
        index = int(digest, 16) % len(candidates)
        return candidates[index]

    def pick_daily_words(
        self,
        languages: list[str],
        level: str,
        count: int,
        target_date: date | None = None,
        user_id: int | None = None,
    ) -> list[WordEntry]:
        """
        Выбирает несколько уникальных слов на день.

        Слова чередуются по языкам пользователя.
        """
        if count <= 0:
            return []

        langs = languages or ["en"]
        target_date = target_date or date.today()
        picked: list[WordEntry] = []
        seen: set[str] = set()

        slot = 0
        max_attempts = count * len(langs) * 4
        attempts = 0

        while len(picked) < count and attempts < max_attempts:
            lang = langs[slot % len(langs)]
            word = self.pick_daily_word(
                language=lang,
                level=level,
                target_date=target_date,
                user_id=user_id,
                slot=slot,
            )
            slot += 1
            attempts += 1
            if word and word.key not in seen:
                seen.add(word.key)
                picked.append(word)

        return picked

    def pick_daily_words_free(
        self,
        languages: list[str],
        level: str,
        per_language: int,
        already_by_lang: dict[str, set[str]],
        target_date: date | None = None,
        user_id: int | None = None,
    ) -> list[WordEntry]:
        """Free: по ``per_language`` слов на каждый изучаемый язык."""
        if per_language <= 0:
            return []

        langs = languages or ["en"]
        target_date = target_date or date.today()
        picked: list[WordEntry] = []
        global_seen: set[str] = set()

        for lang in langs:
            sent_keys = already_by_lang.get(lang, set())
            global_seen.update(sent_keys)
            remaining = per_language - len(sent_keys)
            if remaining <= 0:
                continue

            slot = len(sent_keys)
            added = 0
            attempts = 0
            max_attempts = remaining * 8

            while added < remaining and attempts < max_attempts:
                word = self.pick_daily_word(
                    language=lang,
                    level=level,
                    target_date=target_date,
                    user_id=user_id,
                    slot=slot,
                )
                slot += 1
                attempts += 1
                if word and word.key not in global_seen:
                    global_seen.add(word.key)
                    picked.append(word)
                    added += 1

        return picked

    def pick_quiz_options(
        self,
        correct: WordEntry,
        language: str,
        level: str,
        count: int = 3,
    ) -> list[str]:
        """Генерирует неправильные варианты ответа для квиза."""
        others = [
            w.translation
            for w in self.filter_words(language, level, max_level=False)
            if w.key != correct.key and w.translation != correct.translation
        ]
        seed = correct.key
        digest = hashlib.md5(seed.encode()).hexdigest()
        start = int(digest[:8], 16) % max(len(others), 1) if others else 0

        wrong: list[str] = []
        for i in range(count):
            if not others:
                wrong.append("—")
            else:
                wrong.append(others[(start + i) % len(others)])
        return wrong

    def pick_quiz_word_options(
        self,
        correct: WordEntry,
        language: str,
        level: str,
        count: int = 3,
    ) -> list[str]:
        """Неправильные варианты слова (для обратного квиза)."""
        others = [
            w.word
            for w in self.filter_words(language, level, max_level=False)
            if w.key != correct.key and w.word != correct.word
        ]
        seed = correct.key
        digest = hashlib.md5(seed.encode()).hexdigest()
        start = int(digest[:8], 16) % max(len(others), 1) if others else 0

        wrong: list[str] = []
        for i in range(count):
            if not others:
                wrong.append("—")
            else:
                wrong.append(others[(start + i) % len(others)])
        return wrong

    def sample_quiz_vocabulary(
        self,
        languages: list[str],
        level: str,
        count: int,
    ) -> list[WordEntry]:
        """Случайные слова из словаря по языкам и уровню (для Premium-квиза)."""
        pool: list[WordEntry] = []
        seen: set[str] = set()
        for lang in languages:
            for word in self.filter_words(lang, level, max_level=False):
                if word.key not in seen:
                    seen.add(word.key)
                    pool.append(word)
        if len(pool) <= count:
            return pool
        return random.sample(pool, count)

    @staticmethod
    def format_word_message(
        word: WordEntry,
        *,
        header: str | None = None,
        index: int | None = None,
        total: int | None = None,
    ) -> str:
        """Форматирует красивое сообщение со словом."""
        lang_name = SUPPORTED_LANGUAGES.get(word.language, word.language)
        if header:
            title = header
        elif index and total:
            title = f"📚 Слово {index}/{total}"
        else:
            title = "📚 Слово дня"

        lines = [
            title,
            "",
            f"🌍 {lang_name} · 📊 {word.level}",
            "",
            f"🔤 <b>{h(word.word)}</b>",
            f"🔊 {h(word.transcription)}" if word.transcription else "",
            f"📖 {h(word.translation)}",
        ]
        if word.part_of_speech:
            lines.append(f"🏷 {h(word.part_of_speech)}")

        return "\n".join(line for line in lines if line)

    @staticmethod
    def format_examples(word: WordEntry) -> str:
        """Форматирует примеры с переводами."""
        if not word.examples:
            return "😔 Примеры для этого слова пока не добавлены."

        lines = [f"💬 Примеры — <b>{h(word.word)}</b>", ""]
        for i, example in enumerate(word.examples, 1):
            lines.append(f"{i}. <i>{h(example.text)}</i>")
            if example.translation:
                flag = "🌐" if word.language != "ru" else "🇬🇧"
                lines.append(f"   {flag} {h(example.translation)}")
        return "\n".join(lines)

    @staticmethod
    def xp_for_level(xp_level: int) -> int:
        """Очки, необходимые для следующего уровня."""
        return xp_level * 100

    @staticmethod
    def calculate_level(points: int) -> int:
        """Вычисляет уровень пользователя по очкам."""
        level = 1
        while points >= level * 100:
            level += 1
        return level
