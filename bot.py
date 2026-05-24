from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.config import load_settings
from app.context import AppContext
from app.db import CardRepository
from app.handlers.cards import create_cards_router
from app.handlers.cloze import create_cloze_router
from app.handlers.common import create_common_router
from app.handlers.fallback import create_fallback_router
from app.handlers.quiz import create_quiz_router
from app.handlers.search import create_search_router
from app.services.dictionary_service import DictionaryService
from app.services.example_service import ExampleService
from app.services.quiz_service import QuizEngine
from app.services.translation_service import TranslationService


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    settings = load_settings()

    repo = CardRepository(settings.db_path)
    repo.init_db()

    translator = TranslationService()
    dictionary = DictionaryService()
    quiz_engine = QuizEngine()
    examples = ExampleService(translator)

    # Load dictionary once at startup.
    await asyncio.to_thread(dictionary.load)

    ctx = AppContext(
        repo=repo,
        dictionary=dictionary,
        translator=translator,
        examples=examples,
        quiz_engine=quiz_engine,
    )

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(create_common_router())
    dp.include_router(create_search_router(ctx))
    dp.include_router(create_cards_router(ctx))
    dp.include_router(create_quiz_router(ctx))
    dp.include_router(create_cloze_router(ctx))
    dp.include_router(create_fallback_router())

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="menu", description="Показать меню"),
            BotCommand(command="cancel", description="Отменить текущую команду"),
        ]
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
