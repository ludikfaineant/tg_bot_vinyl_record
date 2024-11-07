import asyncio
from app.bot_instance import bot, dp
from handlers import all_routers

async def main():
    #await bot.delete_webhook(drop_pending_updates=True)
    dp.include_routers(*all_routers)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())