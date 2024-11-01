from aiogram import types, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.types import FSInputFile, ContentType, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from database.database import AsyncSessionLocal
from database.models import User, AlbumVideo
from sqlalchemy.future import select
from services.media_processing import create_rotating_media_video, download_file
from app.bot_instance import bot, dp
from moviepy.editor import AudioFileClip
from datetime import datetime
from data.states import Form
import os
from services.utils import clear_temp_files, process_media_video

router = Router()


@router.message(StateFilter(Form.waiting_for_media), F.content_type.in_([ContentType.PHOTO, ContentType.VIDEO, ContentType.VIDEO_NOTE]))
async def handle_media(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if message.photo:
        media = message.photo[-1]
        media_file_name = f"{user_id}_photo.jpg"
        media_type = 'photo'
    elif message.video:
        media = message.video
        media_file_name = f"{user_id}_video.mp4"
        media_type = 'video'
    elif message.video_note:
        media = message.video_note
        media_file_name = f"{user_id}_video_note.mp4"
        media_type = 'video_note'
    else:
        await message.reply("Пожалуйста, отправьте фото, видео или видеозаметку.")
        return
    
    media_path = await download_file(media.file_id, media_file_name)
    await state.update_data(media_path=media_path, media_type=media_type)
    await message.reply("Медиа получено! Теперь отправьте мне аудио.")
    await state.set_state(Form.waiting_for_audio)


@router.message(StateFilter(Form.waiting_for_audio), F.content_type == ContentType.AUDIO)
async def handle_audio(message: types.Message, state: FSMContext):
    audio_file_name = f"{message.from_user.id}_audio.mp3"
    audio_path = await download_file(message.audio.file_id, audio_file_name)
    await state.update_data(audio_path=audio_path)

    markup = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="Без тайм-кодов")],
        [KeyboardButton(text="С тайм-кодами")]
    ])
    await message.reply("Аудио получено! Какое видео вы хотите создать?", reply_markup=markup)
    await state.set_state(Form.waiting_for_timecodes)

@router.message(StateFilter(Form.waiting_for_timecodes), F.text == "С тайм-кодами")
async def with_timecodes_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data.get('media_path') and data.get('audio_path'):
        await message.answer("Введите тайм-коды в формате: 00:30, 02:15")
    else:
        await message.answer("Сначала отправьте медиа и аудио.")


@router.message(StateFilter(Form.waiting_for_timecodes), F.text == "Без тайм-кодов")
async def without_timecodes_handler(message: types.Message, state: FSMContext):
    """Обработчик для видео без тайм-кодов."""
    await process_media_video(message, state, start=0, end=60)


@router.message(StateFilter(Form.waiting_for_timecodes), F.text.regexp(r"\d{2}:\d{2}"))
async def timecodes_input_handler(message: types.Message, state: FSMContext):
    """Обработчик для ввода тайм-кодов пользователем."""
    try:
        timecodes = {}
        for entry in message.text.split(","):
            time_minutes, time_seconds = map(int, entry.strip().split(":"))
            timecode = time_minutes * 60 + time_seconds
            if 'start' not in timecodes:
                timecodes['start'] = timecode
            else:
                timecodes['end'] = timecode

        if 'start' in timecodes and 'end' in timecodes:
            await process_media_video(message, state, start=timecodes['start'], end=timecodes['end'])
        else:
            await message.reply("Укажите оба тайм-кода: начало и конец.")
    except ValueError:
        await message.reply("Ошибка в формате тайм-кодов. Попробуйте ещё раз, используя формат: 00:30, 02:15")

