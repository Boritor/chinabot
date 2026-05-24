from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values, load_dotenv


@dataclass(slots=True)
class Settings:
    bot_token: str
    db_path: Path


def load_settings() -> Settings:
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"
    load_dotenv(dotenv_path=env_path)

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token and env_path.exists():
        # Handle UTF-8 BOM keys like "\ufeffBOT_TOKEN" gracefully.
        raw_values = dotenv_values(env_path)
        bot_token = str(raw_values.get("\ufeffBOT_TOKEN", "") or "").strip()

    if not bot_token:
        raise RuntimeError("BOT_TOKEN не задан. Создайте .env на основе .env.example")

    db_path_raw = os.getenv("DB_PATH", "data/chinabot.sqlite3")
    db_path = Path(db_path_raw)
    if not db_path.is_absolute():
        db_path = project_root / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    return Settings(bot_token=bot_token, db_path=db_path)