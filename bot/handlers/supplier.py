from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import ADMIN_IDS
from bot.database import db
from bot.keyboards.menus import SUPPLIER_DATE_REPORT, SUPPLIER_MY_DELIVERIES, SUPPLIER_NEW_DELIVERY, supplier_menu
from bot.states import DateRangeReport, NewDelivery
from bot.utils.access import require_role
from bot.utils.date_report import DATE_HINT, fmt, parse_date
from bot.utils.formatting import STATUS_LABELS, format_date_report, format_delivery

router = Router(name="supplier")
router.message.filter(require_role("supplier"))


@router.message(F.text == SUPPLIER_NEW_DELIVERY)
async def start_new_delivery(message: Message, state: FSMContext) -> None:
    await state.set_state(NewDelivery.entering_product_name)
    await message.answer("Маҳсулот номини киритинг:")


@router.message(NewDelivery.entering_product_name, F.text)
async def enter_product_name(message: Message, state: FSMContext) -> None:
    await state.update_data(product_name=message.text.strip())
    await state.set_state(NewDelivery.entering_supplier_kub)
    await message.answer("Маҳсулот ҳажмини (куб) киритинг, масалан: 24.5")


@router.message(NewDelivery.entering_supplier_kub, F.text)
async def enter_supplier_kub(message: Message, state: FSMContext) -> None:
    try:
        supplier_kub = float(message.text.replace(",", "."))
    except ValueError:
        await message.answer("Илтимос, рақам киритинг, масалан: 24.5")
        return

    data = await state.get_data()
    delivery = db.create_delivery(message.from_user.id, data["product_name"], supplier_kub)
    await state.clear()

    await message.answer(
        "✅ <b>Етказиб бериш яратилди!</b>\nАдмин харидорни тайинлайди.\n\n"
        + format_delivery(delivery),
        reply_markup=supplier_menu(),
        parse_mode="HTML",
    )

    for admin_id in ADMIN_IDS:
        await message.bot.send_message(
            admin_id,
            "🔔 <b>Янги етказиб бериш — харидор тайинланмаган</b>\n\n" + format_delivery(delivery),
            parse_mode="HTML",
        )


@router.message(F.text == SUPPLIER_MY_DELIVERIES)
async def my_deliveries(message: Message) -> None:
    deliveries = db.list_deliveries_by_supplier(message.from_user.id)
    if not deliveries:
        await message.answer("Сизда ҳали етказиб беришлар йўқ.")
        return

    for delivery in deliveries[:20]:
        await message.answer(format_delivery(delivery), parse_mode="HTML")


@router.message(F.text == SUPPLIER_DATE_REPORT)
async def supplier_report_start(message: Message, state: FSMContext) -> None:
    await state.update_data(report_for="supplier")
    await state.set_state(DateRangeReport.entering_start_date)
    await message.answer(f"📅 Бошланиш санасини киритинг ({DATE_HINT}):")


@router.message(DateRangeReport.entering_start_date, F.text)
async def supplier_report_enter_start(message: Message, state: FSMContext) -> None:
    iso = parse_date(message.text)
    if iso is None:
        await message.answer(f"Нотўғри формат. {DATE_HINT.capitalize()} киритинг:")
        return
    await state.update_data(date_from=iso)
    await state.set_state(DateRangeReport.entering_end_date)
    await message.answer(f"📅 Тугаш санасини киритинг ({DATE_HINT}):")


@router.message(DateRangeReport.entering_end_date, F.text)
async def supplier_report_enter_end(message: Message, state: FSMContext) -> None:
    iso = parse_date(message.text)
    if iso is None:
        await message.answer(f"Нотўғри формат. {DATE_HINT.capitalize()} киритинг:")
        return

    data = await state.get_data()
    await state.clear()
    date_from, date_to = data["date_from"], iso

    deliveries = db.list_deliveries_in_range(message.from_user.id, None, date_from, date_to)
    await message.answer(
        format_date_report(deliveries, fmt(date_from), fmt(date_to)),
        parse_mode="HTML",
    )
