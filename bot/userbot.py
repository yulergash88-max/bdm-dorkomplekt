"""
Pyrogram userbot — listens to the sales group and processes ОТЧЁТЫ БОТ messages.
Uses a regular Telegram user account (not a bot) so it can read all messages,
including those sent by other bots.
"""

import html
import logging

from pyrogram import Client, filters, idle
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


async def _forward_to_suppliers(text: str) -> None:
    """Send every group message to all active suppliers regardless of whether it's parseable."""
    suppliers = db.list_users_by_role("supplier")
    for s in suppliers:
        if s["telegram_id"] == 0 or not s["is_approved"] or s["is_blocked"]:
            continue
        try:
            await _main_bot.send_message(
                s["telegram_id"],
                f"📨 <b>Гурухдан хабар:</b>\n\n{html.escape(text)}",
                parse_mode="HTML",
            )
        except Exception as exc:
            logger.warning("Userbot: could not forward to supplier %s: %s", s["telegram_id"], exc)


async def _process_sale(text: str) -> None:
    parsed = parse_sale_message(text)
    if parsed is None:
        return

    delivery = db.create_delivery(SYSTEM_SUPPLIER_ID, parsed.product_name, parsed.quantity_kub, parsed.car_number, parsed.sale_datetime)
    logger.info("Userbot: created delivery id=%s product=%r kub=%s", delivery["id"], parsed.product_name, parsed.quantity_kub)

    company_members = db.find_buyer_company(parsed.client_name) if parsed.client_name else []
    if company_members:
        primary = next((m for m in company_members if m["is_buyer_admin"]), company_members[0])
        db.assign_buyer(delivery["id"], primary["telegram_id"])
        assigned = db.get_delivery(delivery["id"])
        for member in company_members:
            await _main_bot.send_message(
                member["telegram_id"],
                "📦 <b>Янги етказиб бериш!</b>\nҚабул қилинг ёки рад этинг:\n\n"
                + format_delivery(assigned),
                reply_markup=accept_reject_keyboard(assigned["id"]),
                parse_mode="HTML",
            )
    else:
        note = (
            f"\n\n⚠️ Номаълум мижоз: «<b>{parsed.client_name}</b>» — харидор компаниясига мос келмади."
            if parsed.client_name else ""
        )
        for admin_id in ADMIN_IDS:
            await _main_bot.send_message(
                admin_id,
                "🔔 <b>Янги етказиб бериш — харидор тайинланмаган</b>"
                + note + "\n\n" + format_delivery(delivery),
                parse_mode="HTML",
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
        await _forward_to_suppliers(text)
        await _process_sale(text)

    await client.start()
    logger.info("Userbot started — listening to group %s", SALES_GROUP_CHAT_ID)
    await idle()
