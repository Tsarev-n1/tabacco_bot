import asyncio
import logging
from os import getenv

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher

from models.models import Base
from handlers import worker, admin, anonymous
from engine import engine

load_dotenv()

TOKEN = getenv("TOKEN")
bot = Bot(token=TOKEN)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    Base.metadata.create_all(engine)
    worker.workers()

    dp = Dispatcher()
    dp.include_router(admin.router)
    dp.include_router(worker.router)
    dp.include_router(anonymous.router)

    anonymous.get_workers(anonymous.workers_id)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == '__main__':
    asyncio.run(main())
