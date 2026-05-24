from __future__ import annotations

import random
import re
from dataclasses import dataclass

from app.models import Card, ClozeQuestion, QuizQuestion
from app.services.example_service import ExampleService


@dataclass(slots=True)
class ClozeResult:
    total: int
    correct: int
    mistakes: list[dict[str, str]]


class QuizEngine:
    def build_card_quiz_question(self, cards: list[Card], asked_card_ids: set[int]) -> QuizQuestion | None:
        if len(cards) < 4:
            return None

        available = [card for card in cards if card.id not in asked_card_ids]
        if not available:
            asked_card_ids.clear()
            available = cards[:]

        correct_card = random.choice(available)
        wrong_cards = [card for card in cards if card.id != correct_card.id]
        distractors = random.sample(wrong_cards, k=3)

        options = [correct_card.meaning_ru, *(card.meaning_ru for card in distractors)]
        random.shuffle(options)

        return QuizQuestion(
            word=correct_card.word,
            correct_answer=correct_card.meaning_ru,
            options=options,
            card_id=correct_card.id,
        )

    async def build_cloze_questions(
        self,
        cards: list[Card],
        count: int,
        example_service: ExampleService,
    ) -> list[ClozeQuestion]:
        if len(cards) < count:
            return []

        chosen_cards = random.sample(cards, k=count)
        questions: list[ClozeQuestion] = []

        for card in chosen_cards:
            examples = await example_service.fetch_examples(card.word, limit=1)
            if examples:
                sentence_full = examples[0].chinese
            else:
                sentence_full = f"我喜欢{card.word}。"

            sentence_with_gap = self._replace_first(sentence_full, card.word, "____")
            if sentence_with_gap == sentence_full:
                sentence_with_gap = f"____：{sentence_full}"

            questions.append(
                ClozeQuestion(
                    card_id=card.id,
                    word=card.word,
                    sentence_full=sentence_full,
                    sentence_with_gap=sentence_with_gap,
                    expected_answer=card.word,
                )
            )

        return questions

    @staticmethod
    def check_cloze_answer(user_answer: str, expected: str) -> bool:
        normalized_user = QuizEngine._normalize(user_answer)
        normalized_expected = QuizEngine._normalize(expected)
        return normalized_user == normalized_expected

    @staticmethod
    def _normalize(text: str) -> str:
        text = text.strip().lower()
        text = re.sub(r"\s+", "", text)
        return text

    @staticmethod
    def _replace_first(text: str, old: str, new: str) -> str:
        idx = text.find(old)
        if idx < 0:
            return text
        return text[:idx] + new + text[idx + len(old) :]
