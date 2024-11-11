from aiogram import types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select
from aiogram_ui import KB, B

from database.database import AsyncSessionLocal
from database.models.user import User
from services.utils import clear_temp_files
from data.callbacks import DefaultCallbacks


router = Router()


@router.message(Command("start"))
async def start_handler(message: types.Message):
    user_id: int = message.from_user.id  # type: ignore
    async with AsyncSessionLocal() as session:
        async with session.begin():
            result = await session.execute(select(User).filter_by(telegram_id=user_id))
            user = result.scalars().first()
            if not user:
                user = User(telegram_id=user_id)
                session.add(user)
            await session.commit()
    markup = KB(B("Записать пластинку", DefaultCallbacks.record))
    await message.answer("Привет!", reply_markup=markup)


@router.callback_query(DefaultCallbacks.record)
async def media(event: types.CallbackQuery):
    await event.message.answer("Отправь мне медиа")  # type: ignore
    await event.answer()


@router.callback_query(DefaultCallbacks.cancel)
async def cancel(event: types.CallbackQuery, state: FSMContext):
    markup = KB(B("Записать пластинку", DefaultCallbacks.record))
    await event.message.answer("Запись отменена", reply_markup=markup)  # type: ignore
    await clear_temp_files(state)
    await event.answer()
