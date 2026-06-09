import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import BOT_TOKEN, PYROGRAM_API_ID, SYSTEM_SUPPLIER_ID, SYSTEM_SUPPLIER_NAME
from bot.database import db
from bot.handlers import admin, buyer, start, supplier
from bot.userbot import run_userbot, set_bot as set_userbot

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    db.ensure_system_supplier(SYSTEM_SUPPLIER_ID, SYSTEM_SUPPLIER_NAME)

    bot = Bot(token=BOT_TOKEN)
    set_userbot(bot)

    dp = Dispatcher()
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(supplier.router)
    dp.include_router(buyer.router)

    await bot.delete_webhook(drop_pending_updates=True)

    tasks = [
        dp.start_polling(bot),
    ]
    if PYROGRAM_API_ID:
        tasks.append(run_userbot())
        logger.info("Pyrogram userbot enabled")

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error("Task %d raised an exception: %s", i, result, exc_info=result)


if __name__ == "__main__":
    asyncio.run(main())
