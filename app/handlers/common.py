from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards import main_menu_kb


def create_common_router() -> Router:
    router = Router()

    @router.message(CommandStart())
    async def start_handler(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer(
            "Привет! Я помогу учить китайский. Выберите действие в меню ниже.",
            reply_markup=main_menu_kb(),
        )

    @router.message(Command("cancel"))
    @router.message(F.text.casefold() == "отменить")
    async def cancel_handler(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer("Действие отменено. Возвращаемся в главное меню.", reply_markup=main_menu_kb())

    @router.message(Command("menu"))
    async def menu_handler(message: Message) -> None:
        await message.answer("Главное меню:", reply_markup=main_menu_kb())

    return router
