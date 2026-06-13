#!/usr/bin/env python3
"""Генератор data/words.json — 100 слов на язык и уровень CEFR (3600 записей)."""

from __future__ import annotations

import json
from pathlib import Path

from level_vocab import LEVEL_VOCAB

OUTPUT = Path(__file__).resolve().parent.parent / "data" / "words.json"
LANGS = ("en", "de", "it", "sr", "ru", "be")
LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
NATIVE_TR = {"ru", "be"}


def ex_en(word: str, tr: str) -> list[dict[str, str]]:
    t = tr.split(",")[0].strip()
    return [
        {"text": f'I know the word "{word}".', "translation": f"Я знаю слово «{t}»."},
        {"text": f"This is {word}.", "translation": f"Это {t}."},
    ]


def ex_de(word: str, tr: str) -> list[dict[str, str]]:
    t = tr.split(",")[0].strip()
    return [
        {"text": f'Ich kenne das Wort „{word}".', "translation": f"Я знаю слово «{t}»."},
        {"text": f"Das ist {word}.", "translation": f"Это {t}."},
    ]


def ex_it(word: str, tr: str) -> list[dict[str, str]]:
    t = tr.split(",")[0].strip()
    return [
        {"text": f'Conosco la parola «{word}».', "translation": f"Я знаю слово «{t}»."},
        {"text": f"Questo è {word}.", "translation": f"Это {t}."},
    ]


def ex_sr(word: str, tr: str) -> list[dict[str, str]]:
    t = tr.split(",")[0].strip()
    return [
        {"text": f'Znam reč „{word}".', "translation": f"Я знаю слово «{t}»."},
        {"text": f"To je {word}.", "translation": f"Это {t}."},
    ]


def ex_native(word: str, tr: str) -> list[dict[str, str]]:
    t = tr.split(",")[0].strip()
    return [
        {"text": f"Я знаю слово «{word}».", "translation": f'I know the word "{t}".'},
        {"text": f"Это — {word}.", "translation": f"This is {t}."},
    ]


EXAMPLE_BUILDERS = {
    "en": ex_en,
    "de": ex_de,
    "it": ex_it,
    "sr": ex_sr,
    "ru": ex_native,
    "be": ex_native,
}


def build() -> list[dict]:
    words: list[dict] = []
    for level in LEVELS:
        for concept, pos, forms in LEVEL_VOCAB[level]:
            for lang in LANGS:
                word, tr = forms[lang]
                key = f"{lang}_{level.lower()}_{concept}"
                examples = EXAMPLE_BUILDERS[lang](word, tr)
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
