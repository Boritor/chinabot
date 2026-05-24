from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.types import Message

from app.keyboards import main_menu_kb


_MAIN_MENU_TEXTS = {
    "Найти слово",
    "Мои карточки",
    "Тест по карточкам",
    "Подбери слово",
    "Создать карточку",
    "Посмотреть карточки",
    "Удалить карточку",
    "Отменить",
}


def create_fallback_router() -> Router:
    router = Router()

    @router.message(StateFilter(None), F.text)
    async def fallback_text(message: Message) -> None:
        text = (message.text or "").strip()
        if not text:
            return

        # Do not interfere with command handlers.
        if text.startswith("/"):
            await message.answer("Команда не распознана. Используйте /start или кнопки меню.", reply_markup=main_menu_kb())
            return

        if text in _MAIN_MENU_TEXTS:
            return

        await message.answer("Выберите команду в меню или используйте /start.", reply_markup=main_menu_kb())

    return router
