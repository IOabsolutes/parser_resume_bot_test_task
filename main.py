from dotenv import load_dotenv
from os import getenv
from time import time
from aiogram import Bot, Dispatcher
from app.handlers import router as search_router
import asyncio

load_dotenv()

TOKEN = getenv('TOKEN')

bot = Bot(token=TOKEN)
dp = Dispatcher()


async def main():
    dp.include_router(search_router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        start_time = time()
        asyncio.run(main())
        end_time = time()
        print("Execution time:", end_time - start_time)
    except KeyboardInterrupt:
        print(f"Bot stopped")
