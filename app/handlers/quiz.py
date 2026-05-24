from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.context import AppContext
from app.keyboards import main_menu_kb, quiz_continue_inline, quiz_options_inline, yes_no_inline
from app.states import QuizStates


def create_quiz_router(ctx: AppContext) -> Router:
    router = Router()

    async def send_next_question(target_message: Message | CallbackQuery, user_id: int, state: FSMContext) -> None:
        cards = ctx.repo.list_cards(user_id)
        if len(cards) < 4:
            await state.clear()
            text = "Для теста нужно минимум 4 карточки."
            if isinstance(target_message, CallbackQuery):
                await target_message.message.answer(text, reply_markup=main_menu_kb())
            else:
                await target_message.answer(text, reply_markup=main_menu_kb())
            return

        session = ctx.quiz_sessions.setdefault(user_id, {"asked": set()})
        asked = session["asked"]
        question = ctx.quiz_engine.build_card_quiz_question(cards=cards, asked_card_ids=asked)
        if not question:
            await state.clear()
            text = "Недостаточно карточек для генерации вопроса."
            if isinstance(target_message, CallbackQuery):
                await target_message.message.answer(text, reply_markup=main_menu_kb())
            else:
                await target_message.answer(text, reply_markup=main_menu_kb())
            return

        session["current"] = question

        text = f"Выберите правильный перевод:\n\n{question.word}"
        markup = quiz_options_inline(question.options)
        if isinstance(target_message, CallbackQuery):
            await target_message.message.answer(text, reply_markup=markup)
        else:
            await target_message.answer(text, reply_markup=markup)

        await state.set_state(QuizStates.answering)

    @router.message(F.text == "Тест по карточкам")
    async def quiz_entrypoint(message: Message, state: FSMContext) -> None:
        await state.set_state(QuizStates.confirm)
        await message.answer(
            "Тест по карточкам: я показываю слово, а вы выбираете перевод из 4 вариантов.",
            reply_markup=yes_no_inline(prefix="qstart"),
        )

    @router.callback_query(QuizStates.confirm, F.data == "qstart:cancel")
    async def quiz_cancel(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        await state.clear()
        await callback.message.answer("Тест отменен.", reply_markup=main_menu_kb())

    @router.callback_query(QuizStates.confirm, F.data == "qstart:start")
    async def quiz_start(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        await send_next_question(callback, callback.from_user.id, state)

    @router.callback_query(QuizStates.answering, F.data.startswith("quiz:"))
    async def quiz_answer(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        user_id = callback.from_user.id

        session = ctx.quiz_sessions.get(user_id)
        if not session or "current" not in session:
            await state.clear()
            await callback.message.answer("Сессия теста не найдена. Начните заново.", reply_markup=main_menu_kb())
            return

        question = session["current"]
        idx_raw = callback.data.split(":", maxsplit=1)[1]
        if not idx_raw.isdigit():
            return
        idx = int(idx_raw)

        if idx < 0 or idx >= len(question.options):
            return

        selected = question.options[idx]
        correct = question.correct_answer
        session["asked"].add(question.card_id)

        if selected == correct:
            await callback.message.answer("Верно!")
        else:
            cards = ctx.repo.list_cards(user_id)
            card = next((c for c in cards if c.id == question.card_id), None)
            if card:
                await callback.message.answer(
                    "Неверно.\n"
                    f"Правильный ответ: {correct}\n\n"
                    f"Карточка:\nСлово: {card.word}\nПиньинь: {card.pinyin}\nЗначение: {card.meaning_ru}"
                )
            else:
                await callback.message.answer(f"Неверно. Правильный ответ: {correct}")

        await state.set_state(QuizStates.continue_prompt)
        await callback.message.answer("Продолжить тест?", reply_markup=quiz_continue_inline())

    @router.callback_query(QuizStates.continue_prompt, F.data == "quiz_next")
    async def quiz_next(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        await send_next_question(callback, callback.from_user.id, state)

    @router.callback_query(QuizStates.continue_prompt, F.data == "quiz_stop")
    async def quiz_stop(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        ctx.quiz_sessions.pop(callback.from_user.id, None)
        await state.clear()
        await callback.message.answer("Тест завершен.", reply_markup=main_menu_kb())

    @router.message(QuizStates.confirm, F.text.casefold() == "отменить")
    @router.message(QuizStates.answering, F.text.casefold() == "отменить")
    @router.message(QuizStates.continue_prompt, F.text.casefold() == "отменить")
    async def quiz_cancel_text(message: Message, state: FSMContext) -> None:
        ctx.quiz_sessions.pop(message.from_user.id, None)
        await state.clear()
        await message.answer("Тест остановлен.", reply_markup=main_menu_kb())

    return router
