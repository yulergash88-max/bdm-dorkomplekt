import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

ADMIN_IDS = {
    int(admin_id)
    for admin_id in os.environ.get("ADMIN_IDS", "").split(",")
    if admin_id.strip()
}

# Placeholder formula: buyer_kub = buyer_tonnage * lab_coefficient.
# The exact tonnage <-> kub conversion rule will be confirmed by the customer later.
KUB_FORMULA_NOTE = "buyer_kub = buyer_tonnage * lab_coefficient"

# Group/channel chat where the company's general sales bot posts "Савдо" notifications.
# Deliveries are auto-created from messages in this chat (see handlers/sales_feed.py).
# Optional: when not set, the sales feed integration is disabled.
_sales_group_chat_id_raw = os.environ.get("SALES_GROUP_CHAT_ID", "").strip()
SALES_GROUP_CHAT_ID = int(_sales_group_chat_id_raw) if _sales_group_chat_id_raw else None

# Synthetic "supplier" user that auto-created deliveries (parsed from the sales feed) are
# attributed to, since deliveries.supplier_id is a required FK to a registered user.
# 0 is never a real Telegram user id, so it's safe to use as a sentinel.
SYSTEM_SUPPLIER_ID = 0
SYSTEM_SUPPLIER_NAME = "Умумий бот (автомат савдо)"

# Pyrogram userbot — reads ОТЧЁТЫ БОТ messages from the group
PYROGRAM_API_ID = int(os.environ.get("PYROGRAM_API_ID", "0") or "0")
PYROGRAM_API_HASH = os.environ.get("PYROGRAM_API_HASH", "").strip()
PYROGRAM_PHONE = os.environ.get("PYROGRAM_PHONE", "").strip()
PYROGRAM_SESSION = os.environ.get("PYROGRAM_SESSION", "").strip()  # for Railway
