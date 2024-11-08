from aiogram.fsm.state import StatesGroup, State



class Form(StatesGroup):
    waiting_for_media = State()
    waiting_for_audio = State()
    waiting_for_timecodes = State()
