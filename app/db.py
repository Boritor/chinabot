from __future__ import annotations

import sqlite3
from pathlib import Path

from app.models import Card


class CardRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    word TEXT NOT NULL,
                    pinyin TEXT NOT NULL,
                    meaning_ru TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, word)
                )
                """
            )
            conn.commit()

    def add_card(self, user_id: int, word: str, pinyin: str, meaning_ru: str) -> bool:
        try:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO cards (user_id, word, pinyin, meaning_ru) VALUES (?, ?, ?, ?)",
                    (user_id, word, pinyin, meaning_ru),
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def list_cards(self, user_id: int) -> list[Card]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, user_id, word, pinyin, meaning_ru FROM cards WHERE user_id = ? ORDER BY word",
                (user_id,),
            ).fetchall()

        return [
            Card(
                id=row["id"],
                user_id=row["user_id"],
                word=row["word"],
                pinyin=row["pinyin"],
                meaning_ru=row["meaning_ru"],
            )
            for row in rows
        ]

    def get_card_by_index(self, user_id: int, index_1_based: int) -> Card | None:
        cards = self.list_cards(user_id)
        if index_1_based < 1 or index_1_based > len(cards):
            return None
        return cards[index_1_based - 1]

    def delete_card_by_index(self, user_id: int, index_1_based: int) -> bool:
        card = self.get_card_by_index(user_id, index_1_based)
        if not card:
            return False

        with self._connect() as conn:
            conn.execute("DELETE FROM cards WHERE id = ?", (card.id,))
            conn.commit()
        return True

    def cards_count(self, user_id: int) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM cards WHERE user_id = ?", (user_id,)).fetchone()
        return int(row["c"])
