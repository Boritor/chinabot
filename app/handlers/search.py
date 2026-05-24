from __future__ import annotations

from aiogram import F, Router
from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.context import AppContext
from app.keyboards import cancel_kb, main_menu_kb
from app.states import SearchStates

BTN_FIND = "\u041d\u0430\u0439\u0442\u0438 \u0441\u043b\u043e\u0432\u043e"
BTN_CARDS = "\u041c\u043e\u0438 \u043a\u0430\u0440\u0442\u043e\u0447\u043a\u0438"
BTN_QUIZ = "\u0422\u0435\u0441\u0442 \u043f\u043e \u043a\u0430\u0440\u0442\u043e\u0447\u043a\u0430\u043c"
BTN_CLOZE = "\u041f\u043e\u0434\u0431\u0435\u0440\u0438 \u0441\u043b\u043e\u0432\u043e"
BTN_CREATE_CARD = "\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u043a\u0430\u0440\u0442\u043e\u0447\u043a\u0443"
BTN_VIEW_CARDS = "\u041f\u043e\u0441\u043c\u043e\u0442\u0440\u0435\u0442\u044c \u043a\u0430\u0440\u0442\u043e\u0447\u043a\u0438"
BTN_DELETE_CARD = "\u0423\u0434\u0430\u043b\u0438\u0442\u044c \u043a\u0430\u0440\u0442\u043e\u0447\u043a\u0443"
BTN_CANCEL = "\u041e\u0442\u043c\u0435\u043d\u0438\u0442\u044c"

_MAIN_MENU_TEXTS = {
    BTN_FIND,
    BTN_CARDS,
    BTN_QUIZ,
    BTN_CLOZE,
    BTN_CREATE_CARD,
    BTN_VIEW_CARDS,
    BTN_DELETE_CARD,
}


def create_search_router(ctx: AppContext) -> Router:
    router = Router()

    async def run_search_query(message: Message, query: str) -> None:
        result = ctx.dictionary.search(query, translator=ctx.translator, limit=12)
        if not result.entries:
            await message.answer(
                "\u041d\u0438\u0447\u0435\u0433\u043e \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u043e. "
                "\u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u0434\u0440\u0443\u0433\u043e\u0435 "
                "\u0441\u043b\u043e\u0432\u043e \u0438\u043b\u0438 \u043f\u0438\u043d\u044c\u0438\u043d\u044c."
            )
            return

        if result.mode == "pinyin":
            lines = ["\u041d\u0430\u0439\u0434\u0435\u043d\u043d\u044b\u0435 \u0441\u043b\u043e\u0432\u0430 \u043f\u043e \u043f\u0438\u043d\u044c\u0438\u043d\u044e:"]
            for idx, entry in enumerate(result.entries[:10], start=1):
                meaning_ru = ctx.translator.en_to_ru("; ".join(entry.definitions_en[:3]))
                lines.append(f"{idx}. {entry.simplified} - {entry.pinyin_toned} - {meaning_ru}")
            await message.answer("\n".join(lines))
            return

        entry = result.entries[0]
        definitions_ru = [ctx.translator.en_to_ru(d) for d in entry.definitions_en[:8]]
        defs_block = "\n".join(f"- {d}" for d in definitions_ru)

        examples = await ctx.examples.fetch_examples(entry.simplified, limit=3)
        if examples:
            examples_block = "\n\n".join(
                f"{i}. {ex.chinese}\n   \u041f\u0435\u0440\u0435\u0432\u043e\u0434: {ex.translation_ru}"
                for i, ex in enumerate(examples, start=1)
            )
        else:
            examples_block = "\u041f\u0440\u0438\u043c\u0435\u0440\u044b \u043f\u043e\u043a\u0430 \u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d\u044b."

        await message.answer(
            f"\u0421\u043b\u043e\u0432\u043e: {entry.simplified}\n"
            f"\u041f\u0438\u043d\u044c\u0438\u043d\u044c: {entry.pinyin_toned}\n"
            f"\u0417\u043d\u0430\u0447\u0435\u043d\u0438\u044f:\n{defs_block}\n\n"
            f"\u041f\u0440\u0438\u043c\u0435\u0440\u044b:\n{examples_block}"
        )

    @router.message(F.text == BTN_FIND)
    async def search_entrypoint(message: Message, state: FSMContext) -> None:
        await state.set_state(SearchStates.waiting_query)
        if message.from_user:
            ctx.search_sessions.add(message.from_user.id)
        await message.answer(
            "\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u0441\u043b\u043e\u0432\u043e \u0434\u043b\u044f \u043f\u043e\u0438\u0441\u043a\u0430: "
            "\u043a\u0438\u0442\u0430\u0439\u0441\u043a\u0438\u0435 \u0438\u0435\u0440\u043e\u0433\u043b\u0438\u0444\u044b, "
            "\u043f\u0438\u043d\u044c\u0438\u043d\u044c (\u043b\u0430\u0442\u0438\u043d\u0438\u0446\u0435\u0439) "
            "\u0438\u043b\u0438 \u0440\u0443\u0441\u0441\u043a\u043e\u0435 \u0441\u043b\u043e\u0432\u043e.\n"
            "\u041f\u0438\u043d\u044c\u0438\u043d\u044c \u043c\u043e\u0436\u043d\u043e \u0432\u0432\u043e\u0434\u0438\u0442\u044c "
            "\u0438 \u0440\u0430\u0437\u0434\u0435\u043b\u044c\u043d\u043e, \u0438 \u0441\u043b\u0438\u0442\u043d\u043e "
            "(\u043d\u0430\u043f\u0440\u0438\u043c\u0435\u0440: ni hao / nihao).\n"
            "\u042f \u043f\u043e\u043a\u0430\u0436\u0443 \u0438\u0435\u0440\u043e\u0433\u043b\u0438\u0444\u044b "
            "(\u0443\u043f\u0440\u043e\u0449\u0435\u043d\u043d\u044b\u0435), \u043f\u0438\u043d\u044c\u0438\u043d\u044c, "
            "\u0437\u043d\u0430\u0447\u0435\u043d\u0438\u044f \u0438 \u043f\u0440\u0438\u043c\u0435\u0440\u044b.",
            reply_markup=cancel_kb(),
        )

    @router.message(SearchStates.waiting_query)
    async def process_search(message: Message, state: FSMContext):
        text = (message.text or "").strip()
        user_id = message.from_user.id if message.from_user else 0
        if not text:
            await message.answer(
                "\u041d\u0443\u0436\u0435\u043d \u0442\u0435\u043a\u0441\u0442\u043e\u0432\u044b\u0439 "
                "\u0437\u0430\u043f\u0440\u043e\u0441. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 "
                "\u0441\u043d\u043e\u0432\u0430."
            )
            return None

        if text.casefold() == BTN_CANCEL.casefold():
            await state.clear()
            if user_id:
                ctx.search_sessions.discard(user_id)
            await message.answer(
                "\u0412\u043e\u0437\u0432\u0440\u0430\u0449\u0430\u0435\u043c\u0441\u044f \u0432 \u043c\u0435\u043d\u044e.",
                reply_markup=main_menu_kb(),
            )
            return None

        if text in _MAIN_MENU_TEXTS or text.startswith("/"):
            await state.clear()
            if user_id:
                ctx.search_sessions.discard(user_id)
            return UNHANDLED

        try:
            await run_search_query(message, text)
        except Exception:
            await message.answer(
                "\u041f\u043e\u0438\u0441\u043a \u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e "
                "\u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d. "
                "\u041f\u043e\u0432\u0442\u043e\u0440\u0438\u0442\u0435 \u043f\u043e\u043f\u044b\u0442\u043a\u0443."
            )
        return None

    @router.message(StateFilter(None), F.text)
    async def process_search_when_state_lost(message: Message, state: FSMContext):
        user_id = message.from_user.id if message.from_user else 0
        if not user_id or user_id not in ctx.search_sessions:
            return UNHANDLED

        text = (message.text or "").strip()
        if not text:
            return UNHANDLED

        if text.casefold() == BTN_CANCEL.casefold():
            ctx.search_sessions.discard(user_id)
            await state.clear()
            await message.answer(
                "\u0412\u043e\u0437\u0432\u0440\u0430\u0449\u0430\u0435\u043c\u0441\u044f \u0432 \u043c\u0435\u043d\u044e.",
                reply_markup=main_menu_kb(),
            )
            return None

        if text in _MAIN_MENU_TEXTS or text.startswith("/"):
            ctx.search_sessions.discard(user_id)
            await state.clear()
            return UNHANDLED

        try:
            await run_search_query(message, text)
        except Exception:
            await message.answer(
                "\u041f\u043e\u0438\u0441\u043a \u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e "
                "\u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d. "
                "\u041f\u043e\u0432\u0442\u043e\u0440\u0438\u0442\u0435 \u043f\u043e\u043f\u044b\u0442\u043a\u0443."
            )
        return None

    return router
