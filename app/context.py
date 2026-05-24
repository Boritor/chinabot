from __future__ import annotations

from dataclasses import dataclass, field

from app.db import CardRepository
from app.services.dictionary_service import DictionaryService
from app.services.example_service import ExampleService
from app.services.quiz_service import QuizEngine
from app.services.translation_service import TranslationService


@dataclass(slots=True)
class AppContext:
    repo: CardRepository
    dictionary: DictionaryService
    translator: TranslationService
    examples: ExampleService
    quiz_engine: QuizEngine
    search_sessions: set[int] = field(default_factory=set)
    quiz_sessions: dict[int, dict] = field(default_factory=dict)
    cloze_sessions: dict[int, dict] = field(default_factory=dict)
