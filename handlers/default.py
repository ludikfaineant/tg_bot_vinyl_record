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
from services.utils import show_album


router = Router()


@router.message(Command("start"))
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


@router.message(StateFilter(Form.start_menu))
async def start_menu_handler(message: types.Message, state: FSMContext):
    if message.text == "Посмотреть альбом":
        await show_album(message, state)
    elif message.text == "Записать видео":
        await message.answer("Отправьте фото или видео, затем аудио.")
        await state.set_state(Form.waiting_for_media)
    else:
        await message.reply("Пожалуйста, выберите корректную опцию.")


@router.message(StateFilter(Form.waiting_for_album_selection))
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


@router.message(StateFilter(Form.confirm_save_to_album))
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


@router.message(StateFilter(Form.waiting_for_video_title))
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
