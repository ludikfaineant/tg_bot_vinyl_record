import os
from aiogram import types, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.types import FSInputFile, ContentType, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from database.database import AsyncSessionLocal
from database.models import User, AlbumVideo
from sqlalchemy.future import select
from services.media_processing import create_rotating_media_video, download_file
from app.bot_instance import bot
from datetime import datetime
from data.states import Form
from moviepy.editor import AudioFileClip

async def clear_temp_files(files):
    for file in files:
        if os.path.exists(file):
            os.remove(file)

async def show_album(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AlbumVideo).filter_by(user_id=user_id))
        album_videos = result.scalars().all()
        if not album_videos:
            await message.reply("Ваш альбом пуст. Отправьте фото или видео для записи.")
            return

        titles = [video.title for video in album_videos]
        await message.reply("Ваш альбом:\n" + "\n".join(titles) + "\nВведите название видео, чтобы получить его.")
    await state.set_state(Form.waiting_for_album_selection)


async def process_media_video(message: types.Message, state: FSMContext, start=0, end=60):
    """Универсальная функция для обработки видео с учётом тайм-кодов."""
    data = await state.get_data()
    media_path = data.get('media_path')
    audio_path = data.get('audio_path')
    media_type = data.get('media_type')

    # Проверяем, что все необходимые данные для обработки есть
    if not media_path or not audio_path:
        await message.reply("Произошла ошибка. Убедитесь, что вы отправили медиа и аудио.")
        await state.clear()
        return

    timecodes = {'start': start, 'end': end}
    video_path = await create_rotating_media_video(media_path, media_type, audio_path, timecodes)
    
    if video_path:
        # Отправляем видео или видео-записку в зависимости от типа медиа
        await bot.send_video_note(message.chat.id, FSInputFile(video_path))
        # Добавляем кнопки для сохранения в альбом
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
            [types.KeyboardButton(text="Сохранить в альбом")],
            [types.KeyboardButton(text="Не сохранять")]
        ])
        await message.reply("Хотите ли вы сохранить это видео в альбом?", reply_markup=markup)
        
        # Обновляем данные состояния с путем видео и переходим к следующему состоянию
        await state.update_data(video_path=video_path)
        await state.set_state(Form.confirm_save_to_album)

        # Очищаем временные файлы
        await clear_temp_files([media_path, audio_path, video_path])
    else:
        audio_clip = AudioFileClip(audio_path)
        audio_duration = f"{int(audio_clip.duration // 60)}:{int(audio_clip.duration % 60):02}"
        await message.reply(f"Введите корректные тайм-коды. Продолжительность аудио: {audio_duration}")

