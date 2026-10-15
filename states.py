from aiogram.fsm.state import State, StatesGroup


class Booking(StatesGroup):
    service = State()
    date = State()
    time = State()
    confirm = State()