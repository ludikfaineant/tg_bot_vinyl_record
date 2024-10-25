import asyncio
from handlers.default import register_handlers
from app.bot_instance import bot, dp

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    register_handlers(dp)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
