from __future__ import annotations

import re

from deep_translator import GoogleTranslator

_CYR_RE = re.compile(r"[\u0400-\u04FF]")
_LAT_RE = re.compile(r"[A-Za-z]")


class TranslationService:
    """Lightweight wrapper around deep-translator with fail-safe behavior."""

    def ru_to_en(self, text: str) -> str:
        return self._translate(text, source="ru", target="en")

    def en_to_ru(self, text: str) -> str:
        return self._translate(text, source="en", target="ru")

    def auto_to_ru(self, text: str) -> str:
        return self._translate(text, source="auto", target="ru")

    def looks_russian(self, text: str) -> bool:
        value = (text or "").strip()
        if not value:
            return False

        cyr = len(_CYR_RE.findall(value))
        lat = len(_LAT_RE.findall(value))
        letters = cyr + lat
        if letters == 0 or cyr == 0:
            return False
        return (cyr / letters) >= 0.55

    def _translate(self, text: str, source: str, target: str) -> str:
        normalized = text.strip()
        if not normalized:
            return normalized

        try:
            translated = GoogleTranslator(source=source, target=target).translate(normalized)
            if not translated:
                return normalized
            return translated
        except Exception:
            return normalized
