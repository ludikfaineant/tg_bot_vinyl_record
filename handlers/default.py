from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.types import FSInputFile, ContentType
from aiogram.fsm.context import FSMContext
from app.database import SessionLocal
from app.models import User, ProcessedVideo
from app.media_processing import create_rotating_media_video, download_file
from app.bot_instance import bot, dp
from moviepy.editor import AudioFileClip  # Для проверки длительности аудио
from datetime import datetime
from data.states import Form
import os

def register_handlers(dp):
    dp.message(Command("start"))(start_handler)
    dp.message(StateFilter(Form.waiting_for_media),
                F.content_type.in_([ContentType.PHOTO, 
                ContentType.VIDEO, ContentType.VIDEO_NOTE]))(handle_media)
    dp.message(StateFilter(Form.waiting_for_audio),
                F.content_type == ContentType.AUDIO)(handle_audio)
    dp.message(StateFilter(Form.waiting_for_timecodes), F.text == "С тайм-кодами")(with_timecodes_handler)
    dp.message(StateFilter(Form.waiting_for_timecodes), F.text == "Без тайм-кодов")(without_timecodes_handler)
    dp.message(StateFilter(Form.waiting_for_timecodes), F.text.regexp(r"\d{2}:\d{2}"))(timecodes_input_handler)



async def start_handler(message: types.Message, state: FSMContext):
    db = SessionLocal()
    user_id = message.from_user.id
    
    user = db.query(User).filter_by(telegram_id=user_id).first()
    if not user:
        user = User(telegram_id=user_id)
        db.add(user)
        db.commit()
    
    await message.answer("Привет! Отправьте фото или видео, затем аудио.")
    await state.set_state(Form.waiting_for_media)
    db.close()

# Обработчик получения фото, видео или видео-записки
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
    
    media_path = await download_file(media.file_id, media_file_name)
    await state.update_data(media_path=media_path, media_type=media_type)
    await message.reply("Медиа получено! Теперь отправьте мне аудио.")
    await state.set_state(Form.waiting_for_audio)

async def handle_audio(message: types.Message, state: FSMContext):
    audio = message.audio
    audio_file_name = f"{message.from_user.id}_audio.mp3"
    
    audio_path = await download_file(audio.file_id, audio_file_name)
    await state.update_data(audio_path=audio_path)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [types.KeyboardButton(text="Без тайм-кодов")],
        [types.KeyboardButton(text="С тайм-кодами")]
    ])
    await message.reply("Аудио получено! Какое видео вы хотите создать?", reply_markup=markup)
    await state.set_state(Form.waiting_for_timecodes)

async def with_timecodes_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if data.get('media_path') and data.get('audio_path'):
        await message.answer("Введите тайм-коды в формате: 00:30, 02:15")
    else:
        await message.answer("Сначала отправьте медиа и аудио.")

async def without_timecodes_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    media_path = data.get('media_path')
    audio_path = data.get('audio_path')
    media_type = data.get('media_type')
    
    if media_path and audio_path:
        video_path = await create_rotating_media_video(media_path, media_type, audio_path)
        
        user_id = message.from_user.id
        db = SessionLocal()
        processed_video = ProcessedVideo(user_id=user_id, video_path=video_path, created_at=datetime.now())
        db.add(processed_video)
        
        processed_videos = db.query(ProcessedVideo).filter_by(user_id=user_id).order_by(ProcessedVideo.created_at.desc()).all()
        if len(processed_videos) > 20:
            for video in processed_videos[20:]:
                db.delete(video)
        
        await bot.send_video(message.chat.id, FSInputFile(video_path))
        os.remove(media_path)
        os.remove(audio_path)
        os.remove(video_path)
        db.commit()
        db.close()
    await state.clear()

async def timecodes_input_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    media_path = data.get('media_path')
    audio_path = data.get('audio_path')
    media_type = data.get('media_type')
    
    timecodes = {}
    for entry in message.text.split(","):
        try:
            time_minutes, time_seconds = map(int, entry.strip().split(":"))
            timecode = time_minutes * 60 + time_seconds
            if not timecodes:
                timecodes['start'] = timecode
            else:
                timecodes['end'] = timecode
        except ValueError:
            await message.reply("Ошибка в формате тайм-кодов. Попробуйте ещё раз, используя формат: 00:30, 02:15")
            return
    
    video_path = await create_rotating_media_video(media_path, media_type, audio_path, timecodes)
    
    if video_path:
        user_id = message.from_user.id
        db = SessionLocal()

        processed_video = ProcessedVideo(user_id=user_id, video_path=video_path, created_at=datetime.now())
        db.add(processed_video)
        
        processed_videos = db.query(ProcessedVideo).filter_by(user_id=user_id).order_by(ProcessedVideo.created_at.desc()).all()
        if len(processed_videos) > 20:
            for video in processed_videos[20:]:
                db.delete(video)
        
        await bot.send_video(message.chat.id, FSInputFile(video_path))
        os.remove(media_path)
        os.remove(audio_path)
        os.remove(video_path)
        db.commit()
        db.close()
        await state.clear()

    else:
        audio_clip = AudioFileClip(audio_path)
        audio_duration = f"{int(audio_clip.duration // 60)}:{int(audio_clip.duration % 60):02}"
        await message.reply(f"Введите корректные тайм-коды. Продолжительность аудио: {audio_duration}")

