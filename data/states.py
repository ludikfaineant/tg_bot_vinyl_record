from aiogram.fsm.state import StatesGroup, State



class Form(StatesGroup):
    waiting_for_media = State()
    waiting_for_audio = State()
    waiting_for_timecodes = State()
    confirm_save_to_album = State()
    waiting_for_video_title = State()  # Состояние для ввода названия
    waiting_for_album_selection = State()
    start_menu = State()