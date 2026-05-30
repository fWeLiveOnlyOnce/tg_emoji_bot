from aiogram.fsm.state import State, StatesGroup


class CreatePackStates(StatesGroup):
    waiting_for_media = State()
    waiting_for_orientation = State()
    waiting_for_grid = State()
    waiting_for_title = State()
    waiting_for_confirmation = State()