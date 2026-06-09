from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.database import db
from bot.keyboards.delivery import accept_reject_keyboard, buyer_weigh_keyboard
from bot.keyboards.input_keyboards import (
    CANCEL_BTN,
    DATE_PRESETS,
    MANUAL_DATE_BTN,
    MANUAL_NUM_BTN,
    date_range_keyboard,
    manual_date_keyboard,
    manual_number_keyboard,
    tonnage_keyboard,
)
from bot.keyboards.menus import BUYER_COMPANY_REPORT, BUYER_DATE_REPORT, BUYER_HISTORY, BUYER_PENDING, buyer_menu
from bot.states import BuyerWeighDelivery, DateRangeReport
from bot.utils.access import require_role
from bot.utils.date_report import DATE_HINT, fmt, parse_date, preset_to_range
from bot.utils.export import deliveries_to_csv, deliveries_to_csv_by_date
from bot.utils.formatting import format_date_report, format_delivery
from bot.utils.reports import build_delivery_stats, format_delivery_stats

router = Router(name="buyer")
router.message.filter(require_role("buyer"))

EXPORT_COMPANY_DELIVERIES_CSV = "export_company_deliveries_csv"

# Tracks last report message per user so it can be deleted before sending a new one
_last_report_msg: dict[int, tuple[int, int]] = {}  # user_id → (chat_id, message_id)


async def _try_delete(bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass


def _company_export_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Excel/CSV юклаб олиш", callback_data=EXPORT_COMPANY_DELIVERIES_CSV)]
        ]
    )


def _company_deliveries(user: dict, status: str | None = None) -> list[dict]:
    """Returns deliveries visible to this buyer — company-wide if a company is set, else own only."""
    if user["company_name"]:
        return db.list_deliveries_by_company(user["company_name"], status=status)
    return db.list_deliveries_by_buyer(user["telegram_id"], status=status)


def _same_company(user: dict, delivery_buyer: dict | None) -> bool:
    """Whether `user` may act on a delivery currently assigned to `delivery_buyer`."""
    if user is None or delivery_buyer is None:
        return False
    if user["company_name"] and delivery_buyer["company_name"]:
        return user["company_name"].strip().lower() == delivery_buyer["company_name"].strip().lower()
    return user["telegram_id"] == delivery_buyer["telegram_id"]


@router.message(F.text == BUYER_PENDING)
async def pending_deliveries(message: Message) -> None:
    user = db.get_user(message.from_user.id)
    deliveries = _company_deliveries(user, status="sent_to_buyer")
    if not deliveries:
        await message.answer("Ҳозирча сизга юборилган янги етказиб беришлар йўқ.")
        return

    for delivery in deliveries:
        await message.answer(
            format_delivery(delivery),
            reply_markup=accept_reject_keyboard(delivery["id"]),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("accept:"))
async def accept_delivery(callback: CallbackQuery) -> None:
    user = db.get_user(callback.from_user.id)
    delivery_id = int(callback.data.split(":")[1])
    delivery = db.get_delivery(delivery_id)
    delivery_buyer = db.get_user(delivery["buyer_id"]) if delivery else None

    if delivery is None or not _same_company(user, delivery_buyer):
        await callback.answer("Топилмади.", show_alert=True)
        return
    if delivery["status"] != "sent_to_buyer":
        await callback.answer("Бу етказиб бериш аллақачон қайта ишланган.", show_alert=True)
        return

    db.assign_buyer(delivery_id, callback.from_user.id)
    db.accept_delivery(delivery_id)

    await callback.answer("Қабул қилинди ✅")
    await callback.message.delete()
    await callback.message.answer(
        "⚖️ <b>Тарози натижасини киритасизми?</b>",
        reply_markup=buyer_weigh_keyboard(delivery_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("buyer_weigh:"))
async def buyer_start_weigh(callback: CallbackQuery, state: FSMContext) -> None:
    delivery_id = int(callback.data.split(":")[1])
    await state.update_data(delivery_id=delivery_id)
    await state.set_state(BuyerWeighDelivery.entering_tonnage)
    await callback.message.edit_text("⚖️ <b>Тарози натижасини тоннада танланг ёки киритинг:</b>", parse_mode="HTML")
    await callback.message.answer("Тоннани танланг:", reply_markup=tonnage_keyboard())
    await callback.answer()


@router.message(BuyerWeighDelivery.entering_tonnage, F.text)
async def buyer_enter_tonnage(message: Message, state: FSMContext) -> None:
    text = message.text.strip()

    if text == CANCEL_BTN:
        await state.clear()
        user = db.get_user(message.from_user.id)
        await message.answer("Бекор қилинди.", reply_markup=buyer_menu(user.get("is_buyer_admin", False)))
        return

    if text == MANUAL_NUM_BTN:
        await state.set_state(BuyerWeighDelivery.entering_manual_tonnage)
        await message.answer("Тоннани ёзинг (масалан: 23.8):", reply_markup=manual_number_keyboard())
        return

    try:
        tonnage = float(text.replace(",", "."))
    except ValueError:
        await message.answer("Рақам танланг ёки ёзинг:", reply_markup=tonnage_keyboard())
        return

    await _finish_weighing(message, state, tonnage)


@router.message(BuyerWeighDelivery.entering_manual_tonnage, F.text)
async def buyer_enter_manual_tonnage(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    if text == CANCEL_BTN:
        await state.clear()
        user = db.get_user(message.from_user.id)
        await message.answer("Бекор қилинди.", reply_markup=buyer_menu(user.get("is_buyer_admin", False)))
        return
    try:
        tonnage = float(text.replace(",", "."))
    except ValueError:
        await message.answer("Рақам киритинг (масалан: 23.8):", reply_markup=manual_number_keyboard())
        return
    await _finish_weighing(message, state, tonnage)


async def _finish_weighing(message: Message, state: FSMContext, tonnage: float) -> None:
    data = await state.get_data()
    await state.clear()

    delivery = db.get_delivery(data["delivery_id"])
    coefficient = db.get_product_coefficient(delivery["product_name"])
    db.set_buyer_tonnage(delivery["id"], tonnage)
    buyer_kub = round(tonnage * coefficient, 3)
    kub_difference = round(buyer_kub - delivery["supplier_kub"], 3)
    db.complete_delivery(delivery["id"], coefficient, buyer_kub, kub_difference)

    updated = db.get_delivery(delivery["id"])
    user = db.get_user(message.from_user.id)
    await message.answer(
        f"✅ <b>Ҳисоб-китоб якунланди!</b>\n🔢 Коэффициент: <b>{coefficient}</b>\n\n" + format_delivery(updated),
        parse_mode="HTML",
        reply_markup=buyer_menu(user.get("is_buyer_admin", False)),
    )

    supplier = db.get_user(delivery["supplier_id"])
    if supplier and supplier["telegram_id"] != 0:
        await message.bot.send_message(
            supplier["telegram_id"],
            "🏁 <b>Ҳисоб-китоб якунланди!</b>\nХаридор тарози натижасини киритди:\n\n" + format_delivery(updated),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("buyer_noweigh:"))
async def buyer_no_weigh(callback: CallbackQuery) -> None:
    delivery_id = int(callback.data.split(":")[1])
    delivery = db.get_delivery(delivery_id)
    if delivery is None or delivery["status"] != "accepted":
        await callback.answer("Бу етказиб бериш аллақачон ишланган.", show_alert=True)
        return

    db.complete_delivery_no_weigh(delivery_id)
    updated = db.get_delivery(delivery_id)

    await callback.answer("Якунланди ✅")
    await callback.message.delete()
    user = db.get_user(callback.from_user.id)
    await callback.message.answer(
        "✅ <b>Тарозисиз якунланди</b>\n\n" + format_delivery(updated),
        parse_mode="HTML",
        reply_markup=buyer_menu(user.get("is_buyer_admin", False)),
    )

    supplier = db.get_user(delivery["supplier_id"])
    if supplier and supplier["telegram_id"] != 0:
        await callback.message.bot.send_message(
            supplier["telegram_id"],
            "✅ <b>Харидор тарозисиз қабул қилди:</b>\n\n" + format_delivery(updated),
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("reject:"))
async def reject_delivery(callback: CallbackQuery) -> None:
    user = db.get_user(callback.from_user.id)
    delivery_id = int(callback.data.split(":")[1])
    delivery = db.get_delivery(delivery_id)
    delivery_buyer = db.get_user(delivery["buyer_id"]) if delivery else None

    if delivery is None or not _same_company(user, delivery_buyer):
        await callback.answer("Топилмади.", show_alert=True)
        return
    if delivery["status"] != "sent_to_buyer":
        await callback.answer("Бу етказиб бериш аллақачон қайта ишланган.", show_alert=True)
        return

    db.reject_delivery(delivery_id)
    await callback.answer("Рад этилди ❌")
    await callback.message.delete()




@router.message(F.text == BUYER_HISTORY)
async def history(message: Message) -> None:
    user = db.get_user(message.from_user.id)
    deliveries = _company_deliveries(user)
    completed = [d for d in deliveries if d["status"] in ("completed", "rejected")]
    if not completed:
        await message.answer("Тарихда ҳали ёзувлар йўқ.")
        return

    for delivery in completed[:20]:
        await message.answer(format_delivery(delivery), parse_mode="HTML")


# --- buyer-admin: company-wide report -----------------------------------------


@router.message(F.text == BUYER_COMPANY_REPORT)
async def company_report(message: Message) -> None:
    user = db.get_user(message.from_user.id)
    if not user["is_buyer_admin"]:
        return

    deliveries = _company_deliveries(user)
    if not deliveries:
        await message.answer("Компания учун етказиб беришлар йўқ.")
        return

    stats = build_delivery_stats(deliveries)
    await message.answer(
        format_delivery_stats(stats),
        reply_markup=_company_export_keyboard(),
    )


@router.message(F.text == BUYER_DATE_REPORT)
async def buyer_report_start(message: Message, state: FSMContext) -> None:
    await state.update_data(report_for="buyer")
    await state.set_state(DateRangeReport.entering_start_date)
    await message.answer("📊 <b>Давр танланг:</b>", reply_markup=date_range_keyboard(), parse_mode="HTML")


@router.message(DateRangeReport.entering_start_date, F.text)
async def report_enter_start(message: Message, state: FSMContext) -> None:
    text = message.text.strip()

    if text == CANCEL_BTN:
        await state.clear()
        user = db.get_user(message.from_user.id)
        await message.answer("Бекор қилинди.", reply_markup=buyer_menu(user.get("is_buyer_admin", False)))
        return

    if text in DATE_PRESETS:
        rng = preset_to_range(text)
        if rng:
            await state.clear()
            await _send_buyer_report(message, rng[0], rng[1])
        return

    if text == MANUAL_DATE_BTN:
        await message.answer(f"📅 Бошланиш санасини киритинг ({DATE_HINT}):", reply_markup=manual_date_keyboard())
        return

    iso = parse_date(text)
    if iso is None:
        await message.answer(f"Нотўғри формат. {DATE_HINT.capitalize()} киритинг ёки давр танланг:", reply_markup=date_range_keyboard())
        return
    await state.update_data(date_from=iso)
    await state.set_state(DateRangeReport.entering_end_date)
    await message.answer(f"📅 Тугаш санасини киритинг ({DATE_HINT}):", reply_markup=manual_date_keyboard())


@router.message(DateRangeReport.entering_end_date, F.text)
async def report_enter_end(message: Message, state: FSMContext) -> None:
    text = message.text.strip()

    if text == CANCEL_BTN:
        await state.clear()
        user = db.get_user(message.from_user.id)
        await message.answer("Бекор қилинди.", reply_markup=buyer_menu(user.get("is_buyer_admin", False)))
        return

    iso = parse_date(text)
    if iso is None:
        await message.answer(f"Нотўғри формат. {DATE_HINT.capitalize()} киритинг:", reply_markup=manual_date_keyboard())
        return

    data = await state.get_data()
    await state.clear()
    await _send_buyer_report(message, data["date_from"], iso)


def _excel_keyboard(role: str, date_from: str, date_to: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(
            text="📥 Excel юклаб олиш",
            callback_data=f"excel_{role}:{date_from}:{date_to}",
        )]]
    )


async def _send_buyer_report(message: Message, date_from: str, date_to: str) -> None:
    user = db.get_user(message.from_user.id)
    if user["company_name"]:
        members = db.list_company_buyers(user["company_name"])
        buyer_ids = [m["telegram_id"] for m in members]
    else:
        buyer_ids = [message.from_user.id]
    if not buyer_ids:
        buyer_ids = [message.from_user.id]

    # Delete previous report message if exists
    prev = _last_report_msg.get(message.from_user.id)
    if prev:
        await _try_delete(message.bot, prev[0], prev[1])

    deliveries = db.list_deliveries_in_range(None, buyer_ids, date_from, date_to)
    sent = await message.answer(
        format_date_report(deliveries, fmt(date_from), fmt(date_to)),
        parse_mode="HTML",
        reply_markup=_excel_keyboard("buyer", date_from, date_to),
    )
    _last_report_msg[message.from_user.id] = (sent.chat.id, sent.message_id)
    await message.answer("📋 Менюга қайтдингиз.", reply_markup=buyer_menu(user.get("is_buyer_admin", False)))


@router.callback_query(F.data.startswith("excel_buyer:"))
async def export_buyer_excel(callback: CallbackQuery) -> None:
    _, date_from, date_to = callback.data.split(":")
    user = db.get_user(callback.from_user.id)
    if user["company_name"]:
        members = db.list_company_buyers(user["company_name"])
        buyer_ids = [m["telegram_id"] for m in members]
    else:
        buyer_ids = [callback.from_user.id]
    if not buyer_ids:
        buyer_ids = [callback.from_user.id]
    deliveries = db.list_deliveries_in_range(None, buyer_ids, date_from, date_to)
    await callback.message.answer_document(
        deliveries_to_csv_by_date(deliveries, fmt(date_from), fmt(date_to))
    )
    await callback.answer()


@router.callback_query(F.data == EXPORT_COMPANY_DELIVERIES_CSV)
async def export_company_deliveries(callback: CallbackQuery) -> None:
    user = db.get_user(callback.from_user.id)
    if user is None or not user["is_buyer_admin"]:
        await callback.answer()
        return

    deliveries = _company_deliveries(user)
    await callback.message.answer_document(deliveries_to_csv(deliveries))
    await callback.answer()
