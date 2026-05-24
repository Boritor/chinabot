from __future__ import annotations

from typing import Any

import aiohttp

from app.models import ExampleSentence
from app.services.translation_service import TranslationService

_NO_RU_TRANSLATION = (
    "(\u043f\u0435\u0440\u0435\u0432\u043e\u0434 \u043d\u0430 \u0440\u0443\u0441\u0441\u043a\u043e\u043c "
    "\u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d)"
)


class ExampleService:
    BASE_URL = "https://api.tatoeba.org/unstable/sentences"

    def __init__(self, translator: TranslationService) -> None:
        self.translator = translator

    async def fetch_examples(self, chinese_word: str, limit: int = 3) -> list[ExampleSentence]:
        params = {
            "lang": "cmn",
            "q": chinese_word,
            "sort": "random",
            "limit": max(10, limit * 8),
            "showtrans": "all",
        }

        try:
            timeout = aiohttp.ClientTimeout(total=12)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(self.BASE_URL, params=params) as response:
                    if response.status != 200:
                        return []
                    payload = await response.json()
        except Exception:
            return []

        data = payload.get("data", [])
        examples: list[ExampleSentence] = []

        for item in data:
            text = str(item.get("text", "")).strip()
            script = str(item.get("script", "")).strip()
            if script and script != "Hans":
                continue
            if not text or chinese_word not in text:
                continue

            translation_ru = self._pick_translation_ru(item.get("translations", []))
            if not translation_ru:
                translation_ru = _NO_RU_TRANSLATION

            examples.append(ExampleSentence(chinese=text, translation_ru=translation_ru))
            if len(examples) >= limit:
                break

        return examples

    def _pick_translation_ru(self, translations: list[dict[str, Any]]) -> str:
        if not translations:
            return ""

        ru = [str(t.get("text", "")).strip() for t in translations if t.get("lang") == "rus"]
        ru = [x for x in ru if x]
        for candidate in ru:
            if self.translator.looks_russian(candidate):
                return candidate

        eng = [str(t.get("text", "")).strip() for t in translations if t.get("lang") == "eng"]
        eng = [x for x in eng if x]
        for candidate in eng:
            translated = self.translator.en_to_ru(candidate)
            if self.translator.looks_russian(translated):
                return translated

        for item in translations:
            candidate = str(item.get("text", "")).strip()
            if not candidate:
                continue
            translated = self.translator.auto_to_ru(candidate)
            if self.translator.looks_russian(translated):
                return translated

        return ""
