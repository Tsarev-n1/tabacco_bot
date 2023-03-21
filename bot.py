import asyncio
import logging
from os import getenv

from dotenv import load_dotenv
from sqlalchemy import create_engine
from aiogram import Bot, Dispatcher

from handlers import worker, admin


load_dotenv()

TOKEN = getenv("TOKEN")


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    engine = create_engine('sqlite:///sqlite.db')
    engine.connect()

    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(admin.router)
    dp.include_router(worker.router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == '__main__':
    asyncio.run(main())