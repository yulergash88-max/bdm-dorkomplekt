import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message

from bot.config import (
    ADMIN_IDS, BOT_TOKEN, PYROGRAM_API_ID,
    SYSTEM_SUPPLIER_ID, SYSTEM_SUPPLIER_NAME,
)
from bot.database import db
from bot.handlers import admin, buyer, start, supplier
from bot.keyboards.delivery import accept_reject_keyboard
from bot.utils.formatting import format_delivery
from bot.utils.sales_parser import parse_sale_message
from bot.userbot import run_userbot, set_bot as set_userbot

logger = logging.getLogger(__name__)


async def _process_sale_text(bot: Bot, text: str) -> bool:
    """Parse text as a sale message and create a delivery. Returns True if processed."""
    parsed = parse_sale_message(text)
    if parsed is None:
        return False

    delivery = db.create_delivery(SYSTEM_SUPPLIER_ID, parsed.product_name, parsed.quantity_kub)
    logger.info("Reports-bot: created delivery id=%s product=%r", delivery["id"], parsed.product_name)

    company_members = db.find_buyer_company(parsed.client_name) if parsed.client_name else []
    if company_members:
        primary = next((m for m in company_members if m["is_buyer_admin"]), company_members[0])
        db.assign_buyer(delivery["id"], primary["telegram_id"])
        assigned = db.get_delivery(delivery["id"])
        for member in company_members:
            await bot.send_message(
                member["telegram_id"],
                "Сизга умумий бот орқали янги етказиб бериш юборилди — қабул қилинг ёки рад этинг:\n\n"
                + format_delivery(assigned),
                reply_markup=accept_reject_keyboard(assigned["id"]),
            )
    else:
        note = (
            f"\n\nНомаълум мижоз: «{parsed.client_name}» — рўйхатдаги ҳеч бир харидор компаниясига мос келмади."
            if parsed.client_name else ""
        )
        for admin_id in ADMIN_IDS:
            await bot.send_message(
                admin_id,
                "Умумий бот хабаридан янги етказиб бериш яратилди — харидор тайинлаш керак:"
                + note + "\n\n" + format_delivery(delivery),
            )
    return True


async def run_reports_bot_polling(main_bot: Bot) -> None:
    """Polls REPORTS_BOT_TOKEN for incoming messages and processes any sale text."""
    reports_bot = Bot(token=REPORTS_BOT_TOKEN)
    dp = Dispatcher()

    @dp.message(F.text)
    async def on_reports_message(message: Message) -> None:
        text = message.text or ""
        logger.info("Reports-bot received: chat=%s text=%r", message.chat.id, text[:80])
        processed = await _process_sale_text(main_bot, text)
        if processed:
            logger.info("Reports-bot: sale processed from chat=%s", message.chat.id)

    logger.info("Starting reports-bot polling...")
    await reports_bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(reports_bot)


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

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
