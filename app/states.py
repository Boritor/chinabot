from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    waiting_query = State()


class CardsStates(StatesGroup):
    menu = State()
    waiting_new_card_word = State()
    waiting_view_number = State()
    waiting_delete_number = State()


class QuizStates(StatesGroup):
    confirm = State()
    answering = State()
    continue_prompt = State()


class ClozeStates(StatesGroup):
    confirm = State()
    choose_count = State()
    answering = State()
    result_choice = State()
