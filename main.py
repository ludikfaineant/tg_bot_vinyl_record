import asyncio
from aiogram import Dispatcher, Bot
from handlers import all_routers
from misc.sqlalchemy_storage import SqlAlchemyStorage
from database.database import AsyncSessionLocal
from settings import settings


async def main():
    bot = Bot(settings.bot.token)

    dp = Dispatcher(storage=SqlAlchemyStorage(AsyncSessionLocal))
    dp["sessionmaker"] = AsyncSessionLocal

    # await bot.delete_webhook(drop_pending_updates=True)
    dp.include_routers(*all_routers)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
