from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.context import AppContext
from app.keyboards import cloze_count_inline, cloze_result_inline, main_menu_kb, yes_no_inline
from app.states import ClozeStates


def create_cloze_router(ctx: AppContext) -> Router:
    router = Router()

    async def ask_current_question(message: Message, user_id: int) -> None:
        session = ctx.cloze_sessions[user_id]
        idx = session["index"]
        questions = session["questions"]
        q = questions[idx]

        await message.answer(
            f"Предложение {idx + 1}/{len(questions)}:\n{q.sentence_with_gap}\n\nВведите пропущенное слово/иероглиф:"
        )

    @router.message(F.text == "Подбери слово")
    async def cloze_entrypoint(message: Message, state: FSMContext) -> None:
        await state.set_state(ClozeStates.confirm)
        await message.answer(
            "Тест 'Подбери слово': я пришлю предложения с пропуском, а вы вводите недостающее слово.",
            reply_markup=yes_no_inline(prefix="clstart"),
        )

    @router.callback_query(ClozeStates.confirm, F.data == "clstart:cancel")
    async def cloze_cancel(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        await state.clear()
        await callback.message.answer("Тест отменен.", reply_markup=main_menu_kb())

    @router.callback_query(ClozeStates.confirm, F.data == "clstart:start")
    async def cloze_start(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        cards_count = ctx.repo.cards_count(callback.from_user.id)
        if cards_count < 10:
            await state.clear()
            await callback.message.answer(
                "Для этого теста нужно минимум 10 карточек.",
                reply_markup=main_menu_kb(),
            )
            return

        await state.set_state(ClozeStates.choose_count)
        await callback.message.answer(
            "Сколько предложений составить?",
            reply_markup=cloze_count_inline(),
        )

    @router.callback_query(ClozeStates.choose_count, F.data.startswith("cloze_count:"))
    async def cloze_choose_count(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        count_raw = callback.data.split(":", maxsplit=1)[1]
        if count_raw not in {"10", "15", "20"}:
            return

        count = int(count_raw)
        cards = ctx.repo.list_cards(callback.from_user.id)
        if len(cards) < count:
            await callback.message.answer(
                f"Для теста на {count} предложений нужно минимум {count} карточек. Сейчас у вас {len(cards)}.")
            return

        questions = await ctx.quiz_engine.build_cloze_questions(cards=cards, count=count, example_service=ctx.examples)
        if len(questions) < count:
            await state.clear()
            await callback.message.answer(
                "Не удалось подготовить достаточно предложений. Попробуйте позже.",
                reply_markup=main_menu_kb(),
            )
            return

        ctx.cloze_sessions[callback.from_user.id] = {
            "questions": questions,
            "index": 0,
            "mistakes": [],
            "correct": 0,
        }

        await state.set_state(ClozeStates.answering)
        await ask_current_question(callback.message, callback.from_user.id)

    @router.message(ClozeStates.answering)
    async def cloze_answer(message: Message, state: FSMContext) -> None:
        if not message.text:
            await message.answer("Введите текстовый ответ.")
            return

        user_id = message.from_user.id
        text = message.text.strip()

        if text.casefold() == "отменить":
            ctx.cloze_sessions.pop(user_id, None)
            await state.clear()
            await message.answer("Тест остановлен.", reply_markup=main_menu_kb())
            return

        session = ctx.cloze_sessions.get(user_id)
        if not session:
            await state.clear()
            await message.answer("Сессия теста не найдена. Начните заново.", reply_markup=main_menu_kb())
            return

        idx = session["index"]
        questions = session["questions"]
        q = questions[idx]

        ok = ctx.quiz_engine.check_cloze_answer(text, q.expected_answer)
        if ok:
            session["correct"] += 1
        else:
            session["mistakes"].append(
                {
                    "num": str(idx + 1),
                    "sentence": q.sentence_full,
                    "user": text,
                    "correct": q.expected_answer,
                }
            )

        session["index"] += 1
        if session["index"] >= len(questions):
            total = len(questions)
            correct = session["correct"]
            mistakes = session["mistakes"]
            err_nums = ", ".join(m["num"] for m in mistakes) if mistakes else "нет"

            await state.set_state(ClozeStates.result_choice)
            await message.answer(
                f"Тест завершен.\nПравильных ответов: {correct}/{total}.\nОшибки в предложениях: {err_nums}",
                reply_markup=cloze_result_inline(),
            )
            return

        await ask_current_question(message, user_id)

    @router.callback_query(ClozeStates.result_choice, F.data == "cloze_errors")
    async def cloze_show_errors(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        session = ctx.cloze_sessions.get(callback.from_user.id)
        if not session:
            await callback.message.answer("Сессия уже завершена.", reply_markup=main_menu_kb())
            return

        mistakes = session["mistakes"]
        if not mistakes:
            ctx.cloze_sessions.pop(callback.from_user.id, None)
            await state.clear()
            await callback.message.answer("Ошибок нет. Отличный результат!", reply_markup=main_menu_kb())
            return

        for m in mistakes:
            await callback.message.answer(
                f"Предложение №{m['num']}: {m['sentence']}\n"
                f"Ваш ответ: {m['user']}\n"
                f"Правильный ответ: {m['correct']}"
            )

        ctx.cloze_sessions.pop(callback.from_user.id, None)
        await state.clear()
        await callback.message.answer("Разбор ошибок завершен.", reply_markup=main_menu_kb())

    @router.callback_query(ClozeStates.result_choice, F.data == "cloze_finish")
    async def cloze_finish(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()
        ctx.cloze_sessions.pop(callback.from_user.id, None)
        await state.clear()
        await callback.message.answer("Готово. Возвращаемся в главное меню.", reply_markup=main_menu_kb())

    @router.message(ClozeStates.confirm, F.text.casefold() == "отменить")
    @router.message(ClozeStates.choose_count, F.text.casefold() == "отменить")
    @router.message(ClozeStates.result_choice, F.text.casefold() == "отменить")
    async def cloze_cancel_text(message: Message, state: FSMContext) -> None:
        ctx.cloze_sessions.pop(message.from_user.id, None)
        await state.clear()
        await message.answer("Тест остановлен.", reply_markup=main_menu_kb())

    return router
