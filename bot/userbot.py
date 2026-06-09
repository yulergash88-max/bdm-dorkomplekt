"""
Pyrogram userbot — listens to the sales group and processes ОТЧЁТЫ БОТ messages.
Uses a regular Telegram user account (not a bot) so it can read all messages,
including those sent by other bots.
"""

import logging

from pyrogram import Client, filters
from pyrogram.types import Message as PyroMessage

from bot.config import (
    ADMIN_IDS,
    PYROGRAM_API_HASH,
    PYROGRAM_API_ID,
    PYROGRAM_PHONE,
    PYROGRAM_SESSION,
    SALES_GROUP_CHAT_ID,
    SYSTEM_SUPPLIER_ID,
)
from bot.database import db
from bot.keyboards.delivery import accept_reject_keyboard
from bot.utils.formatting import format_delivery
from bot.utils.sales_parser import parse_sale_message

logger = logging.getLogger(__name__)

_main_bot = None


def set_bot(bot) -> None:
    global _main_bot
    _main_bot = bot


def _make_client() -> Client:
    if PYROGRAM_SESSION:
        # Railway / server: use session string stored in env var
        return Client(
            name="userbot",
            api_id=PYROGRAM_API_ID,
            api_hash=PYROGRAM_API_HASH,
            session_string=PYROGRAM_SESSION,
        )
    # Local: use session file created by setup_userbot.py
    return Client(
        name="userbot_session",
        api_id=PYROGRAM_API_ID,
        api_hash=PYROGRAM_API_HASH,
        phone_number=PYROGRAM_PHONE,
    )


async def _process_sale(text: str) -> None:
    parsed = parse_sale_message(text)
    if parsed is None:
        return

    delivery = db.create_delivery(SYSTEM_SUPPLIER_ID, parsed.product_name, parsed.quantity_kub)
    logger.info("Userbot: created delivery id=%s product=%r kub=%s", delivery["id"], parsed.product_name, parsed.quantity_kub)

    company_members = db.find_buyer_company(parsed.client_name) if parsed.client_name else []
    if company_members:
        primary = next((m for m in company_members if m["is_buyer_admin"]), company_members[0])
        db.assign_buyer(delivery["id"], primary["telegram_id"])
        assigned = db.get_delivery(delivery["id"])
        for member in company_members:
            await _main_bot.send_message(
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
            await _main_bot.send_message(
                admin_id,
                "Умумий бот хабаридан янги етказиб бериш яратилди — харидор тайинлаш керак:"
                + note + "\n\n" + format_delivery(delivery),
            )


async def run_userbot() -> None:
    if not PYROGRAM_API_ID or not PYROGRAM_API_HASH:
        logger.warning("Userbot: PYROGRAM_* env vars not set — skipping")
        return

    client = _make_client()

    @client.on_message(filters.chat(SALES_GROUP_CHAT_ID))
    async def on_group_message(_client: Client, message: PyroMessage) -> None:
        text = message.text or message.caption or ""
        if not text:
            return
        sender = message.from_user.username if message.from_user else "unknown"
        logger.info("Userbot: from=%s text=%r", sender, text[:80])
        await _process_sale(text)

    await client.start()
    logger.info("Userbot started — listening to group %s", SALES_GROUP_CHAT_ID)
    await client.idle()
