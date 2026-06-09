import logging

from aiogram import F, Router
from aiogram.types import Message

from bot.config import ADMIN_IDS, SALES_GROUP_CHAT_ID, SYSTEM_SUPPLIER_ID
from bot.database import db
from bot.keyboards.delivery import accept_reject_keyboard
from bot.utils.formatting import format_delivery
from bot.utils.sales_parser import parse_sale_message

logger = logging.getLogger(__name__)

# Debug router: catches ALL group-type messages (no chat filter) to log chat_id
debug_router = Router(name="sales_feed_debug")

@debug_router.message(F.chat.type.in_({"group", "supergroup"}))
async def debug_group_message(message: Message) -> None:
    logger.warning(
        "GROUP MSG | chat_id=%s | chat_username=%s | content_type=%s | from_bot=%s | text=%r",
        message.chat.id,
        message.chat.username,
        message.content_type,
        message.from_user.is_bot if message.from_user else "?",
        (message.text or message.caption or "")[:100],
    )

router = Router(name="sales_feed")
router.message.filter(F.chat.id == SALES_GROUP_CHAT_ID)


@router.message()
async def on_sales_feed_message(message: Message) -> None:
    text = message.text or message.caption or ""
    logger.info("SALES_FEED matched | chat=%s | content_type=%s", message.chat.id, message.content_type)
    parsed = parse_sale_message(text)
    if parsed is None:
        return

    delivery = db.create_delivery(SYSTEM_SUPPLIER_ID, parsed.product_name, parsed.quantity_kub)

    company_members = db.find_buyer_company(parsed.client_name) if parsed.client_name else []
    if company_members:
        primary = next((member for member in company_members if member["is_buyer_admin"]), company_members[0])
        db.assign_buyer(delivery["id"], primary["telegram_id"])
        assigned = db.get_delivery(delivery["id"])

        for member in company_members:
            await message.bot.send_message(
                member["telegram_id"],
                "Сизга умумий бот орқали янги етказиб бериш юборилди — "
                "қабул қилинг ёки рад этинг:\n\n" + format_delivery(assigned),
                reply_markup=accept_reject_keyboard(assigned["id"]),
            )
        return

    unknown_client_note = (
        f"\n\nНомаълум мижоз: «{parsed.client_name}» — рўйхатдаги ҳеч бир харидор компаниясига мос келмади."
        if parsed.client_name
        else ""
    )
    for admin_id in ADMIN_IDS:
        await message.bot.send_message(
            admin_id,
            "Умумий бот хабаридан янги етказиб бериш яратилди — харидор тайинлаш керак:"
            + unknown_client_note
            + "\n\n"
            + format_delivery(delivery),
        )
