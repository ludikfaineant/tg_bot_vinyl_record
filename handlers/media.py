from aiogram import types, F, Router
from aiogram.filters import StateFilter
from aiogram.types import ContentType
from aiogram.fsm.context import FSMContext
import asyncio
from aiogram_ui import KB, B

from services.media_processing import download_file
from services.utils import process_media_video
from data.states import Form
from data.callbacks import DefaultCallbacks


router = Router()
semaphore = asyncio.Semaphore(10)
markup_cancel = KB(B("Отменить запись", DefaultCallbacks.cancel))


@router.message(
    F.content_type.in_([ContentType.PHOTO, ContentType.VIDEO, ContentType.VIDEO_NOTE])
)
async def handle_media(message: types.Message, state: FSMContext):
    user_id = message.from_user.id  # type: ignore
    if message.photo:
        media = message.photo[-1]
        media_file_name = f"{user_id}_photo.jpg"
        media_type = "photo"
    elif message.video:
        media = message.video
        media_file_name = f"{user_id}_video.mp4"
        media_type = "video"
    elif message.video_note:
        media = message.video_note
        media_file_name = f"{user_id}_video_note.mp4"
        media_type = "video_note"
    else:
        await message.reply("Пожалуйста, отправьте фото, видео или видеозаметку.")
        return

    media_path = await download_file(media.file_id, media_file_name)
    await state.update_data(media_path=media_path, media_type=media_type)
    markup = KB(B("Отменить запись", DefaultCallbacks.cancel))
    await message.reply(
        "Медиа получено! Теперь отправьте мне аудио.", reply_markup=markup
    )
    await state.set_state(Form.waiting_for_audio)


@router.message(
    StateFilter(Form.waiting_for_audio), F.content_type == ContentType.AUDIO
)
async def handle_audio(message: types.Message, state: FSMContext):
    audio_file_name = f"{message.from_user.id}_audio.mp3"  # type: ignore
    audio_path = await download_file(message.audio.file_id, audio_file_name)  # type: ignore
    await state.update_data(audio_path=audio_path)

    markup = KB(
        B("Без тайм-кодов", DefaultCallbacks.without_time),
        B("С тайм-кодами", DefaultCallbacks.with_time),
        B("Отменить запись", DefaultCallbacks.cancel),
    )

    await message.reply(
        "Аудио получено! Какое видео вы хотите создать?", reply_markup=markup
    )
    await state.set_state(Form.waiting_for_timecodes)


@router.callback_query(DefaultCallbacks.with_time)
async def with_timecodes_handler(event: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if data.get("media_path") and data.get("audio_path"):
        await event.message.answer("Введите тайм-коды в формате: 00:10, 00:45")  # type: ignore
    else:
        await event.message.answer(  # type: ignore
            "Сначала отправьте медиа и аудио.", reply_markup=markup_cancel
        )
    await event.answer()


@router.callback_query(DefaultCallbacks.without_time)
async def without_timecodes_handler(event: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if data.get("media_path") and data.get("audio_path"):
        await process_media_video(event.message, state, start=0, end=60)  # type:ignore
    else:
        await event.message.answer(  # type: ignore
            "Сначала отправьте медиа и аудио.", reply_markup=markup_cancel
        )
    await event.answer()


@router.message(StateFilter(Form.waiting_for_timecodes), F.text.regexp(r"\d{2}:\d{2}"))
async def timecodes_input_handler(message: types.Message, state: FSMContext):
    """Обработчик для ввода тайм-кодов пользователем."""
    async with semaphore:
        try:
            timecodes = {}
            for entry in message.text.split(","):  # type: ignore
                time_minutes, time_seconds = map(int, entry.strip().split(":"))
                timecode = time_minutes * 60 + time_seconds
                if "start" not in timecodes:
                    timecodes["start"] = timecode
                else:
                    timecodes["end"] = timecode

            if "start" in timecodes and "end" in timecodes:
                await process_media_video(
                    message, state, start=timecodes["start"], end=timecodes["end"]
                )
            else:
                await message.reply(
                    "Укажите оба тайм-кода: начало и конец.", reply_markup=markup_cancel
                )
        except ValueError:
            await message.reply(
                "Ошибка в формате тайм-кодов. Попробуйте ещё раз, используя формат: 00:30, 02:15",
                reply_markup=markup_cancel,
            )
