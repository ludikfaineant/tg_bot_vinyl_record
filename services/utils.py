import os
import asyncio
from aiogram import types
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from database.database import AsyncSessionLocal
from database.models import User, AlbumVideo
from sqlalchemy.future import select
from services.media_processing import create_rotating_media_video
from app.bot_instance import bot
from datetime import datetime
from moviepy.editor import AudioFileClip
from data.callbacks import DefaultCallbacks
from aiogram_ui import KB,B


import os
from aiogram.fsm.context import FSMContext

async def clear_temp_files(state: FSMContext):
    data = await state.get_data()
    media_path = data.get('media_path')
    audio_path = data.get('audio_path')
    files_to_remove = [media_path, audio_path]
    for file in files_to_remove:
        if file and os.path.exists(file):
            os.remove(file)
    state.clear()

async def process_media_video(message:types.Message, state: FSMContext, start=0, end=60):
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

        markup = KB(B("Записать еще", DefaultCallbacks.record))    
        message_with_video = await bot.send_video_note(message.chat.id, FSInputFile(video_path), reply_markup=markup)
        os.remove(video_path)
        file_id = message_with_video.video_note.file_id
        user_id = message.from_user.id

        if not file_id:
            await message.reply("Ошибка: видео не найдено.")
            await state.clear()
            return

        async with AsyncSessionLocal() as session:
            async with session.begin():
                result = await session.execute(select(User).filter_by(telegram_id=user_id))
                user = result.scalars().first()
                if user:
                    album_video = AlbumVideo(user_telegram_id=user_id, file_id=file_id, created_at=datetime.now())
                    session.add(album_video)
                    await session.commit()

        await clear_temp_files(state)
    else:
        audio_clip = AudioFileClip(audio_path)
        audio_duration = f"{int(audio_clip.duration // 60)}:{int(audio_clip.duration % 60):02}"
        await message.reply(f"Введите корректные тайм-коды. Продолжительность аудио: {audio_duration}")

