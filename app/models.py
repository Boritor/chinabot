from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DictionaryEntry:
    traditional: str
    simplified: str
    pinyin_numbered: str
    pinyin_toned: str
    definitions_en: list[str]


@dataclass(slots=True)
class ExampleSentence:
    chinese: str
    translation_ru: str


@dataclass(slots=True)
class Card:
    id: int
    user_id: int
    word: str
    pinyin: str
    meaning_ru: str


@dataclass(slots=True)
class QuizQuestion:
    word: str
    correct_answer: str
    options: list[str]
    card_id: int


@dataclass(slots=True)
class ClozeQuestion:
    card_id: int
    word: str
    sentence_full: str
    sentence_with_gap: str
    expected_answer: str
