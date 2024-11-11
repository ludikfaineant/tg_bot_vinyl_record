import asyncio
from aiogram import Dispatcher
from handlers import all_routers
from bot_instance import bot
from misc.sqlalchemy_storage import SqlAlchemyStorage
from database.database import AsyncSessionLocal


async def main():

    dp = Dispatcher(storage=SqlAlchemyStorage(AsyncSessionLocal))
    dp["sessionmaker"] = AsyncSessionLocal

    # await bot.delete_webhook(drop_pending_updates=True)
    dp.include_routers(*all_routers)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
