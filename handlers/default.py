from aiogram import types, F
from aiogram.filters import Command, StateFilter
from aiogram.types import FSInputFile, ContentType, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from app.database import AsyncSessionLocal
from app.models import User, AlbumVideo
from sqlalchemy.future import select
from app.media_processing import create_rotating_media_video, download_file
from app.bot_instance import bot, dp
from moviepy.editor import AudioFileClip
from datetime import datetime
from data.states import Form
import os

def register_handlers(dp):
    dp.message(Command("start"))(start_handler)
    dp.message(StateFilter(Form.waiting_for_media), F.content_type.in_([ContentType.PHOTO, ContentType.VIDEO, ContentType.VIDEO_NOTE]))(handle_media)
    dp.message(StateFilter(Form.waiting_for_audio), F.content_type == ContentType.AUDIO)(handle_audio)
    dp.message(StateFilter(Form.waiting_for_timecodes), F.text == "С тайм-кодами")(with_timecodes_handler)
    dp.message(StateFilter(Form.waiting_for_timecodes), F.text == "Без тайм-кодов")(without_timecodes_handler)
    dp.message(StateFilter(Form.waiting_for_timecodes), F.text.regexp(r"\d{2}:\d{2}"))(timecodes_input_handler)
    dp.message(StateFilter(Form.confirm_save_to_album))(confirm_save_to_album_handler)
    dp.message(StateFilter(Form.waiting_for_video_title))(video_title_handler)
    dp.message(StateFilter(Form.start_menu))(start_menu_handler)
    dp.message(StateFilter(Form.waiting_for_album_selection))(handle_album_selection)

async def start_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(User).filter_by(telegram_id=user_id))
            user = result.scalars().first()
            if not user:
                user = User(telegram_id=user_id)
                session.add(user)
            await session.commit()

    markup = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [KeyboardButton(text="Посмотреть альбом")],
        [KeyboardButton(text="Записать видео")]
    ])
    await message.answer("Привет! Выберите опцию:", reply_markup=markup)
    await state.set_state(Form.start_menu)

async def start_menu_handler(message: types.Message, state: FSMContext):
    if message.text == "Посмотреть альбом":
        await show_album(message, state)
    elif message.text == "Записать видео":
        await message.answer("Отправьте фото или видео, затем аудио.")
        await state.set_state(Form.waiting_for_media)
    else:
        await message.reply("Пожалуйста, выберите корректную опцию.")

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

async def handle_album_selection(message: types.Message, state: FSMContext):
    title = message.text
    user_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(AlbumVideo).filter_by(user_id=user_id, title=title))
        video = result.scalars().first()
        
        if video:
            await bot.send_video(message.chat.id, FSInputFile(video.video_path))
            await message.reply("Вот ваше видео!")
        else:
            await message.reply("Видео с таким названием не найдено.")

    await state.clear()  # Сбрасываем состояние

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

    if not media_path or not audio_path:
        await message.reply("Произошла ошибка. Убедитесь, что вы отправили медиа и аудио.")
        await state.clear()
        return
    
    video_path = await create_rotating_media_video(media_path, media_type, audio_path,{'start':0, 'end':60})
    await bot.send_video(message.chat.id, FSInputFile(video_path))

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
        [types.KeyboardButton(text="Сохранить в альбом")],
        [types.KeyboardButton(text="Не сохранять")]
    ])
    await message.reply("Хотите ли вы сохранить это видео в альбом?", reply_markup=markup)
    await state.update_data(video_path=video_path)
    await state.set_state(Form.confirm_save_to_album)

    await clear_temp_files([media_path, audio_path])

async def confirm_save_to_album_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    if 'video_path' not in data:
        await message.reply("Произошла ошибка. Видео не было создано.")
        await state.finish()
        return

    if message.text == "Сохранить в альбом":
        await message.reply("Введите название для видео:")
        await state.set_state(Form.waiting_for_video_title)
    elif message.text == "Не сохранять":
        await message.reply("Видео не сохранено в альбом.")
        await state.clear()
    else:
        await message.reply("Пожалуйста, выберите корректный вариант: 'Сохранить в альбом' или 'Не сохранять'.")

async def video_title_handler(message: types.Message, state: FSMContext):
    title = message.text
    data = await state.get_data()
    video_path = data.get('video_path')
    user_id = message.from_user.id

    if not video_path:
        await message.reply("Ошибка: видео не найдено.")
        await state.clear()
        return

    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(User).filter_by(telegram_id=user_id))
            user = result.scalars().first()
            if user:
                album_video = AlbumVideo(user_id=user.id, video_path=video_path, title=title, created_at=datetime.now())
                session.add(album_video)

                # Удаляем лишние видео
                result = await session.execute(select(AlbumVideo).filter_by(user_id=user.id).order_by(AlbumVideo.created_at.desc()))
                album_videos = result.scalars().all()
                for video in album_videos[20:]:
                    await session.delete(video)
                    
                await session.commit()
                await message.reply(f"Видео '{title}' сохранено в альбом.")
    await state.clear()

async def timecodes_input_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    media_path = data.get('media_path')
    audio_path = data.get('audio_path')
    media_type = data.get('media_type')

    if not media_path or not audio_path or not media_type:
        await message.reply("Произошла ошибка. Убедитесь, что вы отправили медиа и аудио.")
        await state.clear()
        return

    timecodes = {}
    for entry in message.text.split(","):
        try:
            time_minutes, time_seconds = map(int, entry.strip().split(":"))
            timecode = time_minutes * 60 + time_seconds
            if 'start' not in timecodes:
                timecodes['start'] = timecode
            else:
                timecodes['end'] = timecode
        except ValueError:
            await message.reply("Ошибка в формате тайм-кодов. Попробуйте ещё раз, используя формат: 00:30, 02:15")
            return

    video_path = await create_rotating_media_video(media_path, media_type, audio_path, timecodes)
    if video_path:
        await bot.send_video_note(message.chat.id, FSInputFile(video_path))
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, keyboard=[
            [types.KeyboardButton(text="Сохранить в альбом")],
            [types.KeyboardButton(text="Не сохранять")]
        ])
        await message.reply("Хотите ли вы сохранить это видео в альбом?", reply_markup=markup)
        
        await state.update_data(video_path=video_path)
        await state.set_state(Form.confirm_save_to_album)
        
        await clear_temp_files([media_path, audio_path, video_path])
    else:
        audio_clip = AudioFileClip(audio_path)
        audio_duration = f"{int(audio_clip.duration // 60)}:{int(audio_clip.duration % 60):02}"
        await message.reply(f"Введите корректные тайм-коды. Продолжительность аудио: {audio_duration}")

async def clear_temp_files(files):
    for file in files:
        if os.path.exists(file):
            os.remove(file)
