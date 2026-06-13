#!/usr/bin/env python3
"""Генератор data/words.json — 100 слов на язык и уровень CEFR (3600 записей)."""

from __future__ import annotations

import json
from pathlib import Path

from level_vocab import LEVEL_VOCAB

OUTPUT = Path(__file__).resolve().parent.parent / "data" / "words.json"
LANGS = ("en", "de", "it", "sr", "ru", "be")
EN_TR = {"ru", "be"}
LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")


def ex_foreign(lang: str, word: str, tr: str) -> list[dict[str, str]]:
    t = tr.split(",")[0].strip()
    return [
        {"text": f"This is {word}.", "translation": f"Это {t}."},
        {"text": f"I need {word}.", "translation": f"Мне нужно: {t}."},
    ]


def ex_native(word: str, tr: str) -> list[dict[str, str]]:
    t = tr.split(",")[0].strip()
    return [
        {"text": f"Я знаю слово «{word}».", "translation": f'I know the word "{t}".'},
        {"text": f"Это — {word}.", "translation": f"This is {t}."},
    ]


def build() -> list[dict]:
    words: list[dict] = []
    for level in LEVELS:
        for concept, pos, forms in LEVEL_VOCAB[level]:
            for lang in LANGS:
                word, tr = forms[lang]
                key = f"{lang}_{level.lower()}_{concept}"
                examples = ex_native(word, tr) if lang in EN_TR else ex_foreign(lang, word, tr)
                words.append(
                    {
                        "key": key,
                        "language": lang,
                        "level": level,
                        "word": word,
                        "translation": tr,
                        "transcription": "",
                        "part_of_speech": pos,
                        "examples": examples,
                    }
                )
    return words


def main() -> None:
    data = {"words": build()}
    OUTPUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Written {len(data['words'])} words to {OUTPUT}")
    for level in LEVELS:
        for lang in LANGS:
            count = sum(1 for w in data["words"] if w["level"] == level and w["language"] == lang)
            print(f"  {lang}_{level.lower()}: {count}")


if __name__ == "__main__":
    main()
