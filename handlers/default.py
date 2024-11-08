from aiogram import types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.future import select
from aiogram_ui import KB,B

from database.database import AsyncSessionLocal
from database.models import User
from services.utils import clear_temp_files
from data.states import Form
from data.callbacks import DefaultCallbacks



router = Router()


@router.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
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
async def media(event: types.CallbackQuery, state: FSMContext):
    await event.answer()
    await event.message.answer("Отправь мне медиа")
    await state.set_state(Form.waiting_for_media)

@router.callback_query(DefaultCallbacks.cancel)
async def cancel(event: types.CallbackQuery, state:FSMContext):
    markup = KB(B("Записать пластинку", DefaultCallbacks.record))
    await event.answer()
    await event.message.answer("Запись отменена", reply_markup=markup)
    await clear_temp_files(state)

