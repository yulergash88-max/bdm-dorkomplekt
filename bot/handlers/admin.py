from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import ADMIN_IDS
from bot.database import db
from bot.keyboards.common import ROLE_LABELS
from bot.keyboards.delivery import approve_user_keyboard, assign_buyer_keyboard, weigh_delivery_keyboard
from bot.keyboards.menus import (
    ADMIN_ACCEPTED,
    ADMIN_ADD_USER,
    ADMIN_ALL_DELIVERIES,
    ADMIN_COEFFICIENT,
    ADMIN_BLOCK_USER,
    ADMIN_CHANGE_ROLE,
    ADMIN_EDIT_USER,
    ADMIN_LIST_USERS,
    ADMIN_PENDING_USERS,
    ADMIN_REPORT_DELIVERY_STATS,
    ADMIN_REPORT_USER_ACTIVITY,
    ADMIN_REPORTS_SECTION,
    ADMIN_TOGGLE_BUYER_ADMIN,
    ADMIN_UNASSIGNED,
    ADMIN_USERS_SECTION,
    BACK_TO_ADMIN_MENU,
    admin_menu,
    admin_reports_menu,
    admin_users_menu,
)
from bot.keyboards.users import (
    add_user_role_keyboard,
    block_toggle_keyboard,
    buyer_admin_toggle_keyboard,
    edit_field_keyboard,
    role_pick_keyboard,
    user_list_keyboard,
)
from bot.states import AdminAddUser, AdminEditUser, AdminSetCoefficient, WeighDelivery
from bot.utils.access import require_admin
from bot.utils.export import deliveries_to_csv, users_to_csv
from bot.utils.formatting import format_delivery, format_user
from bot.utils.reports import (
    build_delivery_stats,
    build_user_activity,
    format_delivery_stats,
    format_user_activity,
)

EXPORT_DELIVERIES_CSV = "export_deliveries_csv"
EXPORT_USERS_CSV = "export_users_csv"


def _export_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Excel/CSV юклаб олиш", callback_data=callback_data)]]
    )

router = Router(name="admin")
router.message.filter(require_admin(ADMIN_IDS))

EDIT_FIELD_LABELS = {"full_name": "Исм-фамилия", "phone": "Телефон"}


async def notify_user(message_or_callback, telegram_id: int, text: str) -> None:
    """Best-effort DM — admin-managed users may not have started the bot yet."""
    bot = message_or_callback.bot
    try:
        await bot.send_message(telegram_id, text)
    except (TelegramForbiddenError, TelegramBadRequest):
        pass


# --- menu navigation -------------------------------------------------------


@router.message(F.text == ADMIN_USERS_SECTION)
async def open_users_section(message: Message) -> None:
    await message.answer("Фойдаланувчилар бошқаруви:", reply_markup=admin_users_menu())


@router.message(F.text == ADMIN_REPORTS_SECTION)
async def open_reports_section(message: Message) -> None:
    await message.answer("Ҳисоботлар:", reply_markup=admin_reports_menu())


@router.message(F.text == BACK_TO_ADMIN_MENU)
async def back_to_admin_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Бош менюга қайтдингиз.", reply_markup=admin_menu())


@router.message(F.text == ADMIN_PENDING_USERS)
async def pending_users(message: Message) -> None:
    users = db.list_pending_users()
    if not users:
        await message.answer("Тасдиқ кутаётган фойдаланувчилар йўқ.")
        return

    for user in users:
        await message.answer(
            f"Исми: {user['full_name']}\n"
            f"Роли: {ROLE_LABELS[user['role']]}\n"
            f"Телефон: {user['phone']}\n"
            f"ID: {user['telegram_id']}",
            reply_markup=approve_user_keyboard(user["telegram_id"]),
        )


@router.callback_query(F.data.startswith("approve_user:"))
async def approve_user(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer()
        return

    telegram_id = int(callback.data.split(":")[1])
    db.approve_user(telegram_id)
    await callback.message.edit_text(callback.message.text + "\n\nТасдиқланди ✅")
    await callback.answer()
    await callback.message.bot.send_message(
        telegram_id, "Сиз админ томонидан тасдиқландингиз. /start буйруғини қайта босинг."
    )


@router.message(F.text == ADMIN_UNASSIGNED)
async def unassigned_deliveries(message: Message) -> None:
    deliveries = db.list_unassigned_deliveries()
    if not deliveries:
        await message.answer("Харидор тайинланмаган етказиб беришлар йўқ.")
        return

    buyers = db.list_users_by_role("buyer")
    approved_buyers = [b for b in buyers if b["is_approved"]]
    if not approved_buyers:
        await message.answer(
            "Тасдиқланган харидорлар топилмади — аввал харидорни тасдиқланг."
        )
        return

    for delivery in deliveries:
        await message.answer(
            format_delivery(delivery),
            reply_markup=assign_buyer_keyboard(delivery["id"], approved_buyers),
        )


@router.callback_query(F.data.startswith("assign:"))
async def assign_buyer(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer()
        return

    _, delivery_id_raw, buyer_id_raw = callback.data.split(":")
    delivery_id, buyer_id = int(delivery_id_raw), int(buyer_id_raw)

    delivery = db.get_delivery(delivery_id)
    if delivery is None or delivery["status"] != "new":
        await callback.answer("Бу етказиб бериш аллақачон тайинланган.", show_alert=True)
        return

    buyer = db.get_user(buyer_id)
    db.assign_buyer(delivery_id, buyer_id)
    updated = db.get_delivery(delivery_id)

    await callback.message.edit_text(
        callback.message.text + f"\n\nТайинланди: {buyer['full_name']} ✅"
    )
    await callback.answer()

    await callback.message.bot.send_message(
        buyer_id,
        "Сизга янги етказиб бериш тайинланди:\n\n" + format_delivery(updated),
    )


@router.message(F.text == ADMIN_ALL_DELIVERIES)
async def all_deliveries(message: Message) -> None:
    deliveries = db.list_all_deliveries()
    if not deliveries:
        await message.answer("Етказиб беришлар йўқ.")
        return

    for delivery in deliveries[:30]:
        await message.answer(format_delivery(delivery))


# --- weigh accepted deliveries -----------------------------------------------


@router.message(F.text == ADMIN_ACCEPTED)
async def accepted_deliveries(message: Message) -> None:
    deliveries = db.list_deliveries_by_status("accepted")
    if not deliveries:
        await message.answer("Қабул қилинган ва тарози кутаётган етказиб беришлар йўқ.")
        return

    for delivery in deliveries:
        await message.answer(
            format_delivery(delivery),
            reply_markup=weigh_delivery_keyboard(delivery["id"]),
        )


@router.callback_query(F.data.startswith("weigh:"))
async def start_weigh(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer()
        return

    delivery_id = int(callback.data.split(":")[1])
    delivery = db.get_delivery(delivery_id)
    if delivery is None or delivery["status"] != "accepted":
        await callback.answer("Бу етказиб бериш аллақачон ишланган.", show_alert=True)
        return

    await state.update_data(delivery_id=delivery_id)
    await state.set_state(WeighDelivery.entering_tonnage)
    await callback.message.edit_text(callback.message.text + "\n\n⚖️ Тарози киритилмоқда...")
    await callback.message.answer("Тарози натижасини тоннада киритинг (масалан: 23.8):")
    await callback.answer()


@router.message(WeighDelivery.entering_tonnage, F.text)
async def admin_enter_tonnage(message: Message, state: FSMContext) -> None:
    try:
        tonnage = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Илтимос, рақам киритинг, масалан: 23.8")
        return

    data = await state.get_data()
    await state.clear()

    coefficient_raw = db.get_setting("kub_coefficient")
    try:
        coefficient = float(coefficient_raw or "1.0")
    except ValueError:
        coefficient = 1.0

    delivery = db.get_delivery(data["delivery_id"])
    db.set_buyer_tonnage(delivery["id"], tonnage)
    buyer_kub = round(tonnage * coefficient, 3)
    kub_difference = round(buyer_kub - delivery["supplier_kub"], 3)
    db.complete_delivery(delivery["id"], coefficient, buyer_kub, kub_difference)

    updated = db.get_delivery(delivery["id"])
    await message.answer(
        f"✅ Ҳисоб-китоб якунланди (коэффициент: {coefficient}):\n\n" + format_delivery(updated),
        reply_markup=admin_menu(),
    )

    buyer = db.get_user(delivery["buyer_id"]) if delivery["buyer_id"] else None
    if buyer:
        await message.bot.send_message(
            buyer["telegram_id"],
            "Сизнинг қабул қилган етказиб беришингиз бўйича ҳисоб-китоб якунланди:\n\n"
            + format_delivery(updated),
        )
    supplier = db.get_user(delivery["supplier_id"])
    if supplier and supplier["telegram_id"] != 0:
        await message.bot.send_message(
            supplier["telegram_id"],
            "Сизнинг етказиб беришингиз бўйича ҳисоб-китоб якунланди:\n\n"
            + format_delivery(updated),
        )


# --- add user ---------------------------------------------------------------


@router.message(F.text == ADMIN_ADD_USER)
async def start_add_user(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminAddUser.choosing_role)
    await message.answer(
        "Янги фойдаланувчининг ролини танланг:",
        reply_markup=add_user_role_keyboard(),
    )


@router.callback_query(AdminAddUser.choosing_role, F.data.startswith("add_user_role:"))
async def add_user_choose_role(callback: CallbackQuery, state: FSMContext) -> None:
    role = callback.data.split(":", 1)[1]
    await state.update_data(role=role)
    await callback.message.edit_text(f"Танланган роль: {ROLE_LABELS[role]}")
    await callback.answer()

    if role == "buyer":
        await state.set_state(AdminAddUser.entering_company_name)
        await callback.message.answer("Фойдаланувчининг компания номини киритинг:")
    else:
        await state.set_state(AdminAddUser.entering_phone)
        await callback.message.answer("Фойдаланувчининг телефон рақамини киритинг:")


@router.message(AdminAddUser.entering_company_name, F.text)
async def add_user_enter_company_name(message: Message, state: FSMContext) -> None:
    await state.update_data(company_name=message.text.strip())
    await state.set_state(AdminAddUser.entering_phone)
    await message.answer("Фойдаланувчининг телефон рақамини киритинг:")


@router.message(AdminAddUser.entering_phone, F.text)
async def add_user_enter_phone(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    phone = message.text.strip()

    invite = db.create_pending_invite(phone, data["role"], data.get("company_name"))
    await state.clear()

    lines = [
        "Таклифнома сақланди ✅",
        f"Роли: {ROLE_LABELS[invite['role']]}",
    ]
    if invite.get("company_name"):
        lines.append(f"Компания: {invite['company_name']}")
    lines.append(f"Телефон: {invite['phone']}")
    lines.append(
        "\nФойдаланувчи биринчи марта /start берганда ва шу телефон рақамини юборганда — "
        "исми Telegram акаунтидан автоматик олиниб, ҳисоб фаоллашади."
    )

    await message.answer("\n".join(lines), reply_markup=admin_users_menu())


# --- list users --------------------------------------------------------------


@router.message(F.text == ADMIN_LIST_USERS)
async def list_all_users(message: Message) -> None:
    users = db.list_all_users()
    if not users:
        await message.answer("Фойдаланувчилар йўқ.")
        return

    chunk_size = 10
    for offset in range(0, len(users), chunk_size):
        chunk = users[offset : offset + chunk_size]
        await message.answer("\n\n".join(format_user(user) for user in chunk))


# --- edit user ---------------------------------------------------------------


@router.message(F.text == ADMIN_EDIT_USER)
async def start_edit_user(message: Message) -> None:
    users = db.list_all_users()
    if not users:
        await message.answer("Фойдаланувчилар йўқ.")
        return

    await message.answer(
        "Таҳрирлаш учун фойдаланувчини танланг:",
        reply_markup=user_list_keyboard(users, "edit_user"),
    )


@router.callback_query(F.data.startswith("edit_user:"))
async def edit_user_pick_field(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer()
        return

    telegram_id = int(callback.data.split(":")[1])
    await callback.message.edit_text("Қайси маълумотни таҳрирлаймиз?")
    await callback.message.answer(
        "Майдонни танланг:",
        reply_markup=edit_field_keyboard(telegram_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_field:"))
async def edit_user_enter_value(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer()
        return

    _, telegram_id_raw, field = callback.data.split(":")
    await state.update_data(telegram_id=int(telegram_id_raw), field=field)
    await state.set_state(AdminEditUser.entering_new_value)
    await callback.message.edit_text(f"Янги «{EDIT_FIELD_LABELS[field]}» қийматини киритинг:")
    await callback.answer()


@router.message(AdminEditUser.entering_new_value, F.text)
async def edit_user_save_value(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    telegram_id, field = data["telegram_id"], data["field"]
    new_value = message.text.strip()

    db.update_user(telegram_id, **{field: new_value})
    await state.clear()

    user = db.get_user(telegram_id)
    await message.answer(
        "Маълумот янгиланди:\n\n" + format_user(user),
        reply_markup=admin_users_menu(),
    )
    await notify_user(
        message,
        telegram_id,
        f"Сизнинг «{EDIT_FIELD_LABELS[field]}» маълумотингиз админ томонидан янгиланди.",
    )


# --- change role --------------------------------------------------------------


@router.message(F.text == ADMIN_CHANGE_ROLE)
async def start_change_role(message: Message) -> None:
    users = db.list_all_users()
    if not users:
        await message.answer("Фойдаланувчилар йўқ.")
        return

    await message.answer(
        "Ролини ўзгартирмоқчи бўлган фойдаланувчини танланг:",
        reply_markup=user_list_keyboard(users, "change_role"),
    )


@router.callback_query(F.data.startswith("change_role:"))
async def change_role_pick_new_role(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer()
        return

    telegram_id = int(callback.data.split(":")[1])
    await callback.message.edit_text("Янги ролни танланг:")
    await callback.message.answer(
        "Роль:",
        reply_markup=role_pick_keyboard(telegram_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_role:"))
async def change_role_apply(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer()
        return

    _, telegram_id_raw, role = callback.data.split(":")
    telegram_id = int(telegram_id_raw)

    db.update_user(telegram_id, role=role)
    user = db.get_user(telegram_id)

    await callback.message.edit_text("Роль янгиланди:\n\n" + format_user(user))
    await callback.answer()
    await notify_user(
        callback,
        telegram_id,
        f"Сизнинг ролингиз «{ROLE_LABELS[role]}»га ўзгартирилди. /start буйруғини қайта босинг.",
    )


# --- block / unblock -----------------------------------------------------------


@router.message(F.text == ADMIN_BLOCK_USER)
async def start_block_user(message: Message) -> None:
    users = db.list_all_users()
    if not users:
        await message.answer("Фойдаланувчилар йўқ.")
        return

    await message.answer(
        "Фойдаланувчини танланг:",
        reply_markup=user_list_keyboard(users, "view_block"),
    )


@router.callback_query(F.data.startswith("view_block:"))
async def view_block_status(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer()
        return

    telegram_id = int(callback.data.split(":")[1])
    user = db.get_user(telegram_id)
    if user is None:
        await callback.answer("Топилмади.", show_alert=True)
        return

    await callback.message.edit_text(
        format_user(user),
        reply_markup=block_toggle_keyboard(telegram_id, user["is_blocked"]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_block:"))
async def toggle_block(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer()
        return

    telegram_id = int(callback.data.split(":")[1])
    user = db.get_user(telegram_id)
    if user is None:
        await callback.answer("Топилмади.", show_alert=True)
        return

    if user["is_blocked"]:
        db.unblock_user(telegram_id)
        notice = "Сиз админ томонидан блокдан чиқарилдингиз."
    else:
        db.block_user(telegram_id)
        notice = "Сиз админ томонидан блокландингиз."

    updated = db.get_user(telegram_id)
    await callback.message.edit_text(
        format_user(updated),
        reply_markup=block_toggle_keyboard(telegram_id, updated["is_blocked"]),
    )
    await callback.answer()
    await notify_user(callback, telegram_id, notice)


# --- buyer-admin toggle -------------------------------------------------------


@router.message(F.text == ADMIN_TOGGLE_BUYER_ADMIN)
async def start_toggle_buyer_admin(message: Message) -> None:
    users = db.list_users_by_role("buyer")
    if not users:
        await message.answer("Харидорлар йўқ.")
        return

    await message.answer(
        "Фойдаланувчини танланг:",
        reply_markup=user_list_keyboard(users, "view_buyer_admin"),
    )


@router.callback_query(F.data.startswith("view_buyer_admin:"))
async def view_buyer_admin_status(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer()
        return

    telegram_id = int(callback.data.split(":")[1])
    user = db.get_user(telegram_id)
    if user is None:
        await callback.answer("Топилмади.", show_alert=True)
        return

    await callback.message.edit_text(
        format_user(user),
        reply_markup=buyer_admin_toggle_keyboard(telegram_id, user["is_buyer_admin"]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_buyer_admin:"))
async def toggle_buyer_admin(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer()
        return

    telegram_id = int(callback.data.split(":")[1])
    user = db.get_user(telegram_id)
    if user is None:
        await callback.answer("Топилмади.", show_alert=True)
        return

    if user["is_buyer_admin"]:
        db.update_user(telegram_id, is_buyer_admin=False)
        notice = "Сиз энди харидор админи эмассиз."
    else:
        db.update_user(telegram_id, is_buyer_admin=True)
        notice = "Сиз компаниянгизнинг харидор админи қилиб тайинландингиз."

    updated = db.get_user(telegram_id)
    await callback.message.edit_text(
        format_user(updated),
        reply_markup=buyer_admin_toggle_keyboard(telegram_id, updated["is_buyer_admin"]),
    )
    await callback.answer()
    await notify_user(callback, telegram_id, notice)


# --- coefficient settings -----------------------------------------------------


@router.message(F.text == ADMIN_COEFFICIENT)
async def start_set_coefficient(message: Message, state: FSMContext) -> None:
    value = db.get_setting("kub_coefficient") or "1.0"
    await state.set_state(AdminSetCoefficient.entering_value)
    await message.answer(
        f"⚙️ Жорий коэффициент: <b>{value}</b>\n\n"
        "Янги коэффициент қийматини киритинг (масалан: 1.05):",
        parse_mode="HTML",
    )


@router.message(AdminSetCoefficient.entering_value, F.text)
async def save_coefficient(message: Message, state: FSMContext) -> None:
    try:
        value = float(message.text.replace(",", "."))
        if value <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Илтимос, мусбат рақам киритинг, масалан: 1.05")
        return

    db.set_setting("kub_coefficient", str(value))
    await state.clear()
    await message.answer(
        f"✅ Коэффициент сақланди: <b>{value}</b>\n\nЭнди барча тарози ҳисоб-китобларида шу қиймат ишлатилади.",
        parse_mode="HTML",
        reply_markup=admin_menu(),
    )


# --- reports ------------------------------------------------------------------


@router.message(F.text == ADMIN_REPORT_DELIVERY_STATS)
async def report_delivery_stats(message: Message) -> None:
    deliveries = db.list_all_deliveries()
    if not deliveries:
        await message.answer("Етказиб беришлар йўқ.")
        return

    stats = build_delivery_stats(deliveries)
    await message.answer(
        format_delivery_stats(stats),
        reply_markup=_export_keyboard(EXPORT_DELIVERIES_CSV),
    )


@router.message(F.text == ADMIN_REPORT_USER_ACTIVITY)
async def report_user_activity(message: Message) -> None:
    users = db.list_all_users()
    if not users:
        await message.answer("Фойдаланувчилар йўқ.")
        return

    deliveries = db.list_all_deliveries()
    rows = build_user_activity(users, deliveries)
    await message.answer(
        format_user_activity(rows),
        reply_markup=_export_keyboard(EXPORT_USERS_CSV),
    )


# --- CSV export ----------------------------------------------------------------


@router.callback_query(F.data == EXPORT_DELIVERIES_CSV)
async def export_deliveries(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer()
        return

    deliveries = db.list_all_deliveries()
    await callback.message.answer_document(deliveries_to_csv(deliveries))
    await callback.answer()


@router.callback_query(F.data == EXPORT_USERS_CSV)
async def export_users(callback: CallbackQuery) -> None:
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer()
        return

    users = db.list_all_users()
    await callback.message.answer_document(users_to_csv(users))
    await callback.answer()
