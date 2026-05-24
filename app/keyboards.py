from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Найти слово")],
            [KeyboardButton(text="Мои карточки")],
            [KeyboardButton(text="Тест по карточкам")],
            [KeyboardButton(text="Подбери слово")],
        ],
        resize_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отменить")]],
        resize_keyboard=True,
    )


def cards_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Создать карточку")],
            [KeyboardButton(text="Посмотреть карточки")],
            [KeyboardButton(text="Удалить карточку")],
            [KeyboardButton(text="Отменить")],
        ],
        resize_keyboard=True,
    )


def yes_no_inline(prefix: str = "yn") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Начать", callback_data=f"{prefix}:start"),
                InlineKeyboardButton(text="Отменить", callback_data=f"{prefix}:cancel"),
            ]
        ]
    )


def quiz_options_inline(options: list[str]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=option, callback_data=f"quiz:{idx}")] for idx, option in enumerate(options)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def quiz_continue_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Продолжить тест", callback_data="quiz_next"),
                InlineKeyboardButton(text="Закончить", callback_data="quiz_stop"),
            ]
        ]
    )


def cloze_count_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="10", callback_data="cloze_count:10"),
                InlineKeyboardButton(text="15", callback_data="cloze_count:15"),
                InlineKeyboardButton(text="20", callback_data="cloze_count:20"),
            ]
        ]
    )


def cloze_result_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Показать ошибки", callback_data="cloze_errors"),
                InlineKeyboardButton(text="Завершить", callback_data="cloze_finish"),
            ]
        ]
    )
