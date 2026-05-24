from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from cepy_dict.cedict import DEFAULT_PATH

from app.models import DictionaryEntry
from app.services.translation_service import TranslationService

_CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
_PINYIN_INPUT_RE = re.compile(r"^[a-zA-Z0-9\s'\-\u00fc\u00dcvV:]+$")
_SPLIT_RE = re.compile(r"[^a-zA-Z]+")
_PINYIN_TONE3_RE = re.compile(r"([A-Za-z\u00fc\u00dcvV:]+)([1-5])")

_TONE_MAP_LOWER = {
    "a": "āáǎà",
    "e": "ēéěè",
    "i": "īíǐì",
    "o": "ōóǒò",
    "u": "ūúǔù",
    "ü": "ǖǘǚǜ",
}

_DIALECT_MARKERS = (
    "cantonese",
    "dialect",
    "jyutping",
    "min nan",
    "hokkien",
    "teochew",
    "wu",
    "hakka",
)

_DROP_PREFIXES = (
    "variant of ",
    "old variant of ",
    "erhua variant of ",
    "also written ",
    "see also ",
    "abbr. for ",
    "abbr for ",
    "bound form",
)


@dataclass(slots=True)
class SearchResult:
    mode: str
    entries: list[DictionaryEntry]


class DictionaryService:
    def __init__(self) -> None:
        self._loaded = False
        self._entries: list[DictionaryEntry] = []
        self._by_word: dict[str, list[DictionaryEntry]] = defaultdict(list)
        self._by_pinyin_plain: dict[str, list[DictionaryEntry]] = defaultdict(list)
        self._by_pinyin_compact: dict[str, list[DictionaryEntry]] = defaultdict(list)

    def load(self) -> None:
        if self._loaded:
            return

        for _, traditional, simplified, pinyin_numbered, definitions in self._iter_cepy_entries():
            if not simplified:
                continue

            cleaned_defs = self._filter_definitions(definitions)
            if not cleaned_defs:
                continue

            entry = DictionaryEntry(
                traditional=traditional,
                simplified=simplified,
                pinyin_numbered=pinyin_numbered,
                pinyin_toned=self._to_toned_pinyin(pinyin_numbered),
                definitions_en=cleaned_defs,
            )

            self._entries.append(entry)
            self._by_word[simplified].append(entry)

            pinyin_plain = self._normalize_pinyin_plain(pinyin_numbered)
            if pinyin_plain:
                self._by_pinyin_plain[pinyin_plain].append(entry)
                self._by_pinyin_compact[self._compact_pinyin(pinyin_plain)].append(entry)

        self._loaded = True

    @staticmethod
    def _iter_cepy_entries():
        path = Path(DEFAULT_PATH)
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                trad, _, rest = line.partition(" ")
                simp, _, rest = rest.partition(" [")
                pinyin, _, rest = rest.partition("] ")
                defs = [d.strip() for d in rest.strip(" /\n\t").split("/")]
                yield (line, trad, simp, pinyin, defs)

    def detect_mode(self, query: str) -> str:
        q = query.strip()
        if _CHINESE_RE.search(q):
            return "chinese"
        if _PINYIN_INPUT_RE.fullmatch(q):
            return "pinyin"
        return "russian"

    def search(self, query: str, translator: TranslationService, limit: int = 10) -> SearchResult:
        self.load()
        mode = self.detect_mode(query)
        if mode == "chinese":
            entries = self.search_by_chinese(query, limit=limit)
        elif mode == "pinyin":
            entries = self.search_by_pinyin(query, limit=limit)
        else:
            entries = self.search_by_russian(query, translator, limit=limit)
        return SearchResult(mode=mode, entries=entries)

    def search_by_chinese(self, query: str, limit: int = 10) -> list[DictionaryEntry]:
        self.load()
        q = query.strip()
        if not q:
            return []

        exact = [e for e in self._entries if e.simplified == q or e.traditional == q]
        if exact:
            return self._select_by_relevance(exact, limit=limit)

        contains = [e for e in self._entries if q in e.simplified]
        return self._select_by_relevance(contains, limit=limit)

    def search_by_pinyin(self, pinyin: str, limit: int = 15) -> list[DictionaryEntry]:
        self.load()
        q_plain = self._normalize_pinyin_plain(pinyin)
        if not q_plain:
            return []

        q_compact = self._compact_pinyin(q_plain)
        entries = list(self._by_pinyin_plain.get(q_plain, []))
        if not entries:
            entries = list(self._by_pinyin_compact.get(q_compact, []))

        if not entries:
            for key, values in self._by_pinyin_compact.items():
                if key.startswith(q_compact):
                    entries.extend(values)
                if len(entries) >= limit * 6:
                    break

        selected = self._select_by_relevance(entries, limit=limit, compact_by_word=True)
        selected.sort(key=lambda e: (len(e.simplified), e.simplified))
        return selected[:limit]

    def search_by_russian(
        self,
        query_ru: str,
        translator: TranslationService,
        limit: int = 10,
    ) -> list[DictionaryEntry]:
        self.load()

        q_ru = query_ru.strip().lower()
        if not q_ru:
            return []

        q_en = (translator.ru_to_en(query_ru) or "").lower().strip()
        search_text = q_en if q_en else q_ru
        search_variants = self._build_search_variants(search_text)

        tokens_set: set[str] = set()
        for variant in search_variants:
            for token in _SPLIT_RE.split(variant):
                if len(token) >= 2:
                    tokens_set.add(token)
        tokens = sorted(tokens_set)

        candidates: list[DictionaryEntry] = []
        for entry in self._entries:
            defs = " ; ".join(entry.definitions_en).lower()
            if not defs:
                continue

            if any(v in defs for v in search_variants) or any(t in defs for t in tokens):
                candidates.append(entry)

        return self._select_by_relevance(
            candidates,
            limit=limit,
            search_text=search_text,
            tokens=tokens,
            compact_by_word=True,
            search_variants=search_variants,
        )

    def _select_by_relevance(
        self,
        entries: list[DictionaryEntry],
        limit: int,
        search_text: str = "",
        tokens: list[str] | None = None,
        compact_by_word: bool = False,
        search_variants: list[str] | None = None,
    ) -> list[DictionaryEntry]:
        if not entries:
            return []

        tokens = tokens or []
        search_variants = search_variants or [search_text] if search_text else []

        grouped: dict[str, list[DictionaryEntry]] = defaultdict(list)
        for e in entries:
            grouped[e.simplified].append(e)

        merged_entries: list[DictionaryEntry] = []
        for word, group in grouped.items():
            merged_entries.append(
                self._merge_word_entries(
                    word,
                    group,
                    search_text=search_text,
                    tokens=tokens,
                    search_variants=search_variants,
                )
            )

        merged_entries.sort(
            key=lambda e: (
                -self._entry_score(
                    e,
                    search_text=search_text,
                    tokens=tokens,
                    search_variants=search_variants,
                ),
                len(e.simplified),
                e.simplified,
            )
        )

        if compact_by_word:
            seen: set[str] = set()
            compact: list[DictionaryEntry] = []
            for e in merged_entries:
                if e.simplified in seen:
                    continue
                seen.add(e.simplified)
                compact.append(e)
            merged_entries = compact

        return merged_entries[:limit]

    def _merge_word_entries(
        self,
        word: str,
        group: list[DictionaryEntry],
        search_text: str = "",
        tokens: list[str] | None = None,
        search_variants: list[str] | None = None,
    ) -> DictionaryEntry:
        tokens = tokens or []
        search_variants = search_variants or [search_text] if search_text else []

        sorted_group = sorted(
            group,
            key=lambda e: -self._entry_score(
                e,
                search_text=search_text,
                tokens=tokens,
                search_variants=search_variants,
            ),
        )
        best = sorted_group[0]
        best_pinyin = best.pinyin_numbered

        merged_defs: list[str] = []
        seen_defs: set[str] = set()

        same_reading = [e for e in sorted_group if e.pinyin_numbered == best_pinyin]
        has_non_surname = any(
            any(not d.lower().startswith("surname ") for d in e.definitions_en) for e in same_reading
        )

        for e in same_reading:
            for d in e.definitions_en:
                if has_non_surname and d.lower().startswith("surname "):
                    continue
                key = d.casefold()
                if key in seen_defs:
                    continue
                seen_defs.add(key)
                merged_defs.append(d)
                if len(merged_defs) >= 12:
                    break
            if len(merged_defs) >= 12:
                break

        return DictionaryEntry(
            traditional=best.traditional,
            simplified=best.simplified,
            pinyin_numbered=best.pinyin_numbered,
            pinyin_toned=best.pinyin_toned,
            definitions_en=merged_defs,
        )

    def _entry_score(
        self,
        entry: DictionaryEntry,
        search_text: str = "",
        tokens: list[str] | None = None,
        search_variants: list[str] | None = None,
    ) -> int:
        tokens = tokens or []
        search_variants = search_variants or [search_text] if search_text else []

        score = 0
        defs = entry.definitions_en
        lower_defs = [d.lower() for d in defs]

        if any(d.startswith("surname ") for d in lower_defs):
            score -= 15

        if any("classifier" in d or d.startswith("cl:") for d in lower_defs):
            score -= 8

        non_meta_count = 0
        for d in lower_defs:
            if not (d.startswith("surname ") or "classifier" in d or d.startswith("cl:")):
                non_meta_count += 1
        score += min(non_meta_count * 3, 15)

        if search_text:
            match_scores = [
                self._definition_match_score(
                    d,
                    search_text=search_text,
                    tokens=tokens,
                    search_variants=search_variants,
                )
                for d in lower_defs
            ]
            match_scores = sorted(match_scores, reverse=True)
            if match_scores:
                score += match_scores[0]
            if len(match_scores) > 1:
                score += match_scores[1] // 3

        score += max(0, 4 - len(entry.simplified) * 2)
        return score

    @staticmethod
    def _definition_match_score(
        definition: str,
        search_text: str,
        tokens: list[str],
        search_variants: list[str],
    ) -> int:
        points = 0
        glosses = [g.strip() for g in definition.split(";") if g.strip()]

        # If translation produced a long phrase (e.g. "functional programming"),
        # do not let exact phrase match dominate over core token matches.
        phrase_like = " " in search_text
        if search_text == definition:
            points += 10 if phrase_like else 24
        elif f" {search_text} " in f" {definition} ":
            points += 6 if phrase_like else 10
        elif search_text in definition:
            points += 3 if phrase_like else 5

        for gloss in glosses:
            normalized_gloss = gloss.strip("()[] ")
            if normalized_gloss == search_text:
                points += 12 if phrase_like else 36
            elif normalized_gloss.startswith(f"{search_text} "):
                points += 4 if phrase_like else 6

            for variant in search_variants:
                if not variant or variant == search_text:
                    continue
                if normalized_gloss == variant:
                    points += 26
                elif normalized_gloss.startswith(f"{variant} "):
                    points += 7
                elif f" {variant} " in f" {normalized_gloss} ":
                    points += 4

        for token in tokens:
            if f" {token} " in f" {definition} ":
                points += 4
            elif token in definition:
                points += 1

        return points

    @staticmethod
    def _build_search_variants(search_text: str) -> list[str]:
        variants: list[str] = []
        seen: set[str] = set()

        def add(value: str) -> None:
            val = value.strip().lower()
            if not val or val in seen:
                return
            seen.add(val)
            variants.append(val)

        add(search_text)
        words = [w for w in _SPLIT_RE.split(search_text) if len(w) >= 3]
        for w in words:
            add(w)
            if w.endswith("ing") and len(w) > 5:
                add(w[:-3])

        if words:
            add(words[-1])

        return variants

    @staticmethod
    def _filter_definitions(definitions: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()

        for raw in definitions:
            d = re.sub(r"\s+", " ", raw.strip())
            if not d:
                continue

            d = re.sub(r"(?:^|;)\s*CL:[^;]*", "", d, flags=re.IGNORECASE)
            d = re.sub(r"(?:^|;)\s*also pr\. \[[^\]]+\]", "", d, flags=re.IGNORECASE)
            d = re.sub(r"\s*;\s*", "; ", d).strip(" ;")
            if not d:
                continue

            dl = d.lower()
            if any(marker in dl for marker in _DIALECT_MARKERS):
                continue
            if "taiwan pr." in dl:
                continue
            if any(dl.startswith(prefix) for prefix in _DROP_PREFIXES):
                continue
            if dl.startswith("see "):
                continue
            if dl.startswith("used in "):
                continue

            key = d.casefold()
            if key in seen:
                continue
            seen.add(key)
            result.append(d)

        return result

    @staticmethod
    def _normalize_pinyin_plain(text: str) -> str:
        lowered = text.lower().replace("u:", "v").replace("\u00fc", "v")
        normalized = unicodedata.normalize("NFD", lowered)
        normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
        normalized = re.sub(r"[1-5]", "", normalized)
        normalized = re.sub(r"[^a-z\s'\-v]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    @staticmethod
    def _compact_pinyin(pinyin_plain: str) -> str:
        return re.sub(r"[\s'\-]+", "", pinyin_plain)

    @staticmethod
    def _to_toned_pinyin(numbered: str) -> str:
        text = (numbered or "").strip()
        if not text:
            return text

        normalized = text.replace("u:", "ü").replace("U:", "Ü")

        def repl(match: re.Match[str]) -> str:
            syllable = match.group(1)
            tone = int(match.group(2))
            return DictionaryService._apply_tone_to_syllable(syllable, tone)

        return _PINYIN_TONE3_RE.sub(repl, normalized)

    @staticmethod
    def _apply_tone_to_syllable(syllable: str, tone: int) -> str:
        base = syllable.replace("u:", "ü").replace("U:", "Ü").replace("v", "ü").replace("V", "Ü")
        if tone <= 0 or tone >= 5:
            return base

        lower = base.lower()
        mark_index = DictionaryService._find_tone_vowel_index(lower)
        if mark_index < 0:
            return base

        marked_char = DictionaryService._mark_vowel(base[mark_index], tone)
        return base[:mark_index] + marked_char + base[mark_index + 1 :]

    @staticmethod
    def _find_tone_vowel_index(syllable_lower: str) -> int:
        if "a" in syllable_lower:
            return syllable_lower.index("a")
        if "e" in syllable_lower:
            return syllable_lower.index("e")
        if "ou" in syllable_lower:
            return syllable_lower.index("o")

        for idx in range(len(syllable_lower) - 1, -1, -1):
            if syllable_lower[idx] in {"a", "e", "i", "o", "u", "ü"}:
                return idx
        return -1

    @staticmethod
    def _mark_vowel(ch: str, tone: int) -> str:
        lower = ch.lower()
        if lower not in _TONE_MAP_LOWER:
            return ch

        marked = _TONE_MAP_LOWER[lower][tone - 1]
        if ch.isupper():
            return marked.upper()
        return marked
