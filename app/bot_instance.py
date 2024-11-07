from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher
from app.config import API_TOKEN



bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
dp["bot"] = bot