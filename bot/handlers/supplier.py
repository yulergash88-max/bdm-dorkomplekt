from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.database import db
from bot.keyboards.input_keyboards import (
    CANCEL_BTN,
    DATE_PRESETS,
    MANUAL_DATE_BTN,
    date_range_keyboard,
    manual_date_keyboard,
)
from bot.keyboards.menus import SUPPLIER_DATE_REPORT, SUPPLIER_MY_DELIVERIES, supplier_menu
from bot.states import DateRangeReport
from bot.utils.access import require_role
from bot.utils.date_report import DATE_HINT, fmt, parse_date, preset_to_range
from bot.utils.export import deliveries_to_csv_by_date
from bot.utils.formatting import STATUS_LABELS, format_date_report, format_delivery

router = Router(name="supplier")
router.message.filter(require_role("supplier"))

_last_report_msg: dict[int, tuple[int, int]] = {}


async def _try_delete(bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass



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
    await message.answer("📊 <b>Давр танланг:</b>", reply_markup=date_range_keyboard(), parse_mode="HTML")


@router.message(DateRangeReport.entering_start_date, F.text)
async def supplier_report_enter_start(message: Message, state: FSMContext) -> None:
    text = message.text.strip()

    if text == CANCEL_BTN:
        await state.clear()
        await message.answer("Бекор қилинди.", reply_markup=supplier_menu())
        return

    if text in DATE_PRESETS:
        rng = preset_to_range(text)
        if rng:
            await state.clear()
            await _send_supplier_report(message, rng[0], rng[1])
        return

    if text == MANUAL_DATE_BTN:
        await message.answer(f"📅 Бошланиш санасини киритинг ({DATE_HINT}):", reply_markup=manual_date_keyboard())
        return

    iso = parse_date(text)
    if iso is None:
        await message.answer("Нотўғри формат. Давр танланг ёки санани киритинг:", reply_markup=date_range_keyboard())
        return
    await state.update_data(date_from=iso)
    await state.set_state(DateRangeReport.entering_end_date)
    await message.answer(f"📅 Тугаш санасини киритинг ({DATE_HINT}):", reply_markup=manual_date_keyboard())


@router.message(DateRangeReport.entering_end_date, F.text)
async def supplier_report_enter_end(message: Message, state: FSMContext) -> None:
    text = message.text.strip()

    if text == CANCEL_BTN:
        await state.clear()
        await message.answer("Бекор қилинди.", reply_markup=supplier_menu())
        return

    iso = parse_date(text)
    if iso is None:
        await message.answer(f"Нотўғри формат. {DATE_HINT.capitalize()} киритинг:", reply_markup=manual_date_keyboard())
        return

    data = await state.get_data()
    await state.clear()
    await _send_supplier_report(message, data["date_from"], iso)


async def _send_supplier_report(message: Message, date_from: str, date_to: str) -> None:
    prev = _last_report_msg.get(message.from_user.id)
    if prev:
        await _try_delete(message.bot, prev[0], prev[1])

    deliveries = db.list_deliveries_in_range(message.from_user.id, None, date_from, date_to)
    sent = await message.answer(
        format_date_report(deliveries, fmt(date_from), fmt(date_to)),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="📥 Excel юклаб олиш", callback_data=f"excel_supplier:{date_from}:{date_to}:{message.from_user.id}")
        ]]),
    )
    _last_report_msg[message.from_user.id] = (sent.chat.id, sent.message_id)
    await message.answer("📋 Менюга қайтдингиз.", reply_markup=supplier_menu())


@router.callback_query(F.data.startswith("excel_supplier:"))
async def export_supplier_excel(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    date_from, date_to, supplier_id = parts[1], parts[2], int(parts[3])
    deliveries = db.list_deliveries_in_range(supplier_id, None, date_from, date_to)
    await callback.message.answer_document(
        deliveries_to_csv_by_date(deliveries, fmt(date_from), fmt(date_to))
    )
    await callback.answer()
