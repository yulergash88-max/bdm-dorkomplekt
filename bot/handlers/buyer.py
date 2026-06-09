from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.database import db
from bot.keyboards.delivery import accept_reject_keyboard, buyer_weigh_keyboard
from bot.keyboards.menus import BUYER_COMPANY_REPORT, BUYER_DATE_REPORT, BUYER_HISTORY, BUYER_PENDING, buyer_menu
from bot.states import BuyerWeighDelivery, DateRangeReport
from bot.utils.access import require_role
from bot.utils.date_report import DATE_HINT, fmt, parse_date
from bot.utils.export import deliveries_to_csv
from bot.utils.formatting import format_date_report, format_delivery
from bot.utils.reports import build_delivery_stats, format_delivery_stats

router = Router(name="buyer")
router.message.filter(require_role("buyer"))

EXPORT_COMPANY_DELIVERIES_CSV = "export_company_deliveries_csv"


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

    await callback.message.edit_text(callback.message.text + "\n\nҲолат: Қабул қилинди ✅")
    await callback.answer()
    await callback.message.answer(
        "Тарози натижасини киритасизми?",
        reply_markup=buyer_weigh_keyboard(delivery_id),
    )


@router.callback_query(F.data.startswith("buyer_weigh:"))
async def buyer_start_weigh(callback: CallbackQuery, state: FSMContext) -> None:
    delivery_id = int(callback.data.split(":")[1])
    await state.update_data(delivery_id=delivery_id)
    await state.set_state(BuyerWeighDelivery.entering_tonnage)
    await callback.message.edit_text("Тарози натижасини тоннада киритинг (масалан: 23.8):")
    await callback.answer()


@router.message(BuyerWeighDelivery.entering_tonnage, F.text)
async def buyer_enter_tonnage(message: Message, state: FSMContext) -> None:
    try:
        tonnage = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Илтимос, рақам киритинг, масалан: 23.8")
        return

    data = await state.get_data()
    await state.clear()

    delivery = db.get_delivery(data["delivery_id"])
    coefficient = db.get_product_coefficient(delivery["product_name"])
    db.set_buyer_tonnage(delivery["id"], tonnage)
    buyer_kub = round(tonnage * coefficient, 3)
    kub_difference = round(buyer_kub - delivery["supplier_kub"], 3)
    db.complete_delivery(delivery["id"], coefficient, buyer_kub, kub_difference)

    updated = db.get_delivery(delivery["id"])
    await message.answer(
        f"✅ Ҳисоб-китоб якунланди (коэффициент: {coefficient}):\n\n" + format_delivery(updated),
    )

    supplier = db.get_user(delivery["supplier_id"])
    if supplier and supplier["telegram_id"] != 0:
        await message.bot.send_message(
            supplier["telegram_id"],
            "Харидор тарози натижасини киритди, ҳисоб-китоб якунланди:\n\n" + format_delivery(updated),
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

    await callback.message.edit_text("✅ Тарозисиз якунланди:\n\n" + format_delivery(updated))
    await callback.answer()

    supplier = db.get_user(delivery["supplier_id"])
    if supplier and supplier["telegram_id"] != 0:
        await callback.message.bot.send_message(
            supplier["telegram_id"],
            "Харидор етказиб беришни тарозисиз қабул қилди:\n\n" + format_delivery(updated),
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
    await callback.message.edit_text(callback.message.text + "\n\nҲолат: Рад этилди ❌")
    await callback.answer()




@router.message(F.text == BUYER_HISTORY)
async def history(message: Message) -> None:
    user = db.get_user(message.from_user.id)
    deliveries = _company_deliveries(user)
    completed = [d for d in deliveries if d["status"] in ("completed", "rejected")]
    if not completed:
        await message.answer("Тарихда ҳали ёзувлар йўқ.")
        return

    for delivery in completed[:20]:
        await message.answer(format_delivery(delivery))


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
    await message.answer(f"📅 Бошланиш санасини киритинг ({DATE_HINT}):")


@router.message(DateRangeReport.entering_start_date, F.text)
async def report_enter_start(message: Message, state: FSMContext) -> None:
    iso = parse_date(message.text)
    if iso is None:
        await message.answer(f"Нотўғри формат. {DATE_HINT.capitalize()} киритинг:")
        return
    await state.update_data(date_from=iso)
    await state.set_state(DateRangeReport.entering_end_date)
    await message.answer(f"📅 Тугаш санасини киритинг ({DATE_HINT}):")


@router.message(DateRangeReport.entering_end_date, F.text)
async def report_enter_end(message: Message, state: FSMContext) -> None:
    iso = parse_date(message.text)
    if iso is None:
        await message.answer(f"Нотўғри формат. {DATE_HINT.capitalize()} киритинг:")
        return

    data = await state.get_data()
    await state.clear()
    date_from, date_to = data["date_from"], iso

    user = db.get_user(message.from_user.id)
    if user["company_name"]:
        members = db.list_company_buyers(user["company_name"])
        buyer_ids = [m["telegram_id"] for m in members]
    else:
        buyer_ids = [message.from_user.id]

    deliveries = db.list_deliveries_in_range(None, buyer_ids, date_from, date_to)
    await message.answer(
        format_date_report(deliveries, fmt(date_from), fmt(date_to)),
        parse_mode="HTML",
    )


@router.callback_query(F.data == EXPORT_COMPANY_DELIVERIES_CSV)
async def export_company_deliveries(callback: CallbackQuery) -> None:
    user = db.get_user(callback.from_user.id)
    if user is None or not user["is_buyer_admin"]:
        await callback.answer()
        return

    deliveries = _company_deliveries(user)
    await callback.message.answer_document(deliveries_to_csv(deliveries))
    await callback.answer()
