from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.context import AppContext
from app.keyboards import cards_menu_kb, cancel_kb, main_menu_kb
from app.states import CardsStates


def create_cards_router(ctx: AppContext) -> Router:
    router = Router()

    @router.message(F.text == "Мои карточки")
    async def cards_entrypoint(message: Message, state: FSMContext) -> None:
        if message.from_user:
            ctx.search_sessions.discard(message.from_user.id)
        await state.set_state(CardsStates.menu)
        await message.answer(
            "Карточки помогают учить слова: можно создать, посмотреть и удалить карточку.",
            reply_markup=cards_menu_kb(),
        )

    @router.message(StateFilter(None, CardsStates.menu), F.text == "Создать карточку")
    async def cards_create_start(message: Message, state: FSMContext) -> None:
        await state.set_state(CardsStates.waiting_new_card_word)
        await message.answer(
            "Введите китайское слово/иероглиф. Я найду чтение и значение и создам карточку.",
            reply_markup=cancel_kb(),
        )

    @router.message(CardsStates.waiting_new_card_word)
    async def cards_create_finish(message: Message, state: FSMContext) -> None:
        if not message.text:
            await message.answer("Нужен текстовый ввод.")
            return

        text = message.text.strip()
        if text.casefold() == "отменить":
            await state.set_state(CardsStates.menu)
            await message.answer("Действие отменено.", reply_markup=cards_menu_kb())
            return

        entries = ctx.dictionary.search_by_chinese(text, limit=1)
        if not entries:
            await message.answer("Слово не найдено в словаре. Попробуйте другое.")
            return

        entry = entries[0]
        meaning_ru = ctx.translator.en_to_ru("; ".join(entry.definitions_en[:2]))
        created = ctx.repo.add_card(
            user_id=message.from_user.id,
            word=entry.simplified,
            pinyin=entry.pinyin_toned,
            meaning_ru=meaning_ru,
        )

        await state.set_state(CardsStates.menu)
        if created:
            await message.answer(
                f"Карточка создана:\n{entry.simplified} — {entry.pinyin_toned} — {meaning_ru}",
                reply_markup=cards_menu_kb(),
            )
        else:
            await message.answer("Такая карточка уже есть.", reply_markup=cards_menu_kb())

    @router.message(StateFilter(None, CardsStates.menu), F.text == "Посмотреть карточки")
    async def cards_view_list(message: Message, state: FSMContext) -> None:
        cards = ctx.repo.list_cards(message.from_user.id)
        if not cards:
            await message.answer("У вас пока нет карточек.")
            return

        words = "\n".join(f"{idx}. {card.word}" for idx, card in enumerate(cards, start=1))
        await state.set_state(CardsStates.waiting_view_number)
        await message.answer(
            f"Ваши карточки:\n{words}\n\nВведите номер карточки для просмотра.",
            reply_markup=cancel_kb(),
        )

    @router.message(CardsStates.waiting_view_number)
    async def cards_view_number(message: Message, state: FSMContext) -> None:
        if not message.text:
            await message.answer("Введите номер карточки.")
            return

        text = message.text.strip()
        if text.casefold() == "отменить":
            await state.set_state(CardsStates.menu)
            await message.answer("Возвращаемся в раздел карточек.", reply_markup=cards_menu_kb())
            return

        if not text.isdigit():
            await message.answer("Нужно ввести число (номер карточки).")
            return

        card = ctx.repo.get_card_by_index(message.from_user.id, int(text))
        if not card:
            await message.answer("Некорректный номер. Попробуйте снова.")
            return

        await state.set_state(CardsStates.menu)
        await message.answer(
            f"Карточка:\nСлово: {card.word}\nПиньинь: {card.pinyin}\nЗначение: {card.meaning_ru}",
            reply_markup=cards_menu_kb(),
        )

    @router.message(StateFilter(None, CardsStates.menu), F.text == "Удалить карточку")
    async def cards_delete_start(message: Message, state: FSMContext) -> None:
        cards = ctx.repo.list_cards(message.from_user.id)
        if not cards:
            await message.answer("Удалять пока нечего: карточек нет.")
            return

        words = "\n".join(f"{idx}. {card.word}" for idx, card in enumerate(cards, start=1))
        await state.set_state(CardsStates.waiting_delete_number)
        await message.answer(
            f"Введите номер карточки для удаления:\n{words}",
            reply_markup=cancel_kb(),
        )

    @router.message(CardsStates.waiting_delete_number)
    async def cards_delete_finish(message: Message, state: FSMContext) -> None:
        if not message.text:
            await message.answer("Введите номер карточки.")
            return

        text = message.text.strip()
        if text.casefold() == "отменить":
            await state.set_state(CardsStates.menu)
            await message.answer("Удаление отменено.", reply_markup=cards_menu_kb())
            return

        if not text.isdigit():
            await message.answer("Нужно ввести число (номер карточки).")
            return

        ok = ctx.repo.delete_card_by_index(message.from_user.id, int(text))
        await state.set_state(CardsStates.menu)

        if ok:
            await message.answer("Карточка удалена.", reply_markup=cards_menu_kb())
        else:
            await message.answer("Не удалось удалить: неверный номер.", reply_markup=cards_menu_kb())

    @router.message(CardsStates.menu, F.text == "Отменить")
    async def cards_exit_to_main(message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer("Возвращаемся в главное меню.", reply_markup=main_menu_kb())

    return router
