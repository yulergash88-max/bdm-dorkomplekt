from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import ADMIN_IDS
from bot.database import db
from bot.keyboards.common import ROLE_LABELS, phone_request_keyboard, role_choice_keyboard
from bot.keyboards.menus import admin_menu, buyer_menu, supplier_menu
from bot.states import Registration

router = Router(name="start")


def menu_for(user: dict):
    if user["role"] == "supplier":
        return supplier_menu()
    if user["role"] == "buyer":
        return buyer_menu(user["is_buyer_admin"])
    return admin_menu()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()

    if message.from_user.id in ADMIN_IDS:
        await message.answer(
            "👋 <b>Ассалому алейкум, Админ!</b>\n\nБошқарув менюси қуйида 👇",
            reply_markup=admin_menu(),
            parse_mode="HTML",
        )
        return

    user = db.get_user(message.from_user.id)
    if user is None:
        await message.answer(
            "👋 <b>Ассалому алейкум!</b>\n\n"
            "Давом этиш учун 📱 телефон рақамингизни юборинг.\n\n"
            "<i>Агар сизни админ олдиндан тизимга қўшган бўлса — "
            "ҳисобингиз шу рақам орқали автоматик фаоллашади.</i>",
            reply_markup=phone_request_keyboard(),
            parse_mode="HTML",
        )
        await state.set_state(Registration.entering_phone)
        return

    if user["is_blocked"]:
        await message.answer("⛔ <b>Ҳисобингиз блокланган.</b>\nАдминга мурожаат қилинг.", parse_mode="HTML")
        return

    if not user["is_approved"]:
        await message.answer(
            "⏳ <b>Рўйхатдан ўтдингиз.</b>\n\nАдмин тасдиғини кутинг — тасдиқлангач сизга хабар берилади.",
            parse_mode="HTML",
        )
        return

    await message.answer(
        f"✅ <b>Хуш келибсиз, {user['full_name']}!</b>\n🎭 {ROLE_LABELS[user['role']]}",
        reply_markup=menu_for(user),
        parse_mode="HTML",
    )


@router.message(Registration.entering_phone, F.contact)
async def enter_phone_contact(message: Message, state: FSMContext) -> None:
    await handle_phone(message, state, message.contact.phone_number)


@router.message(Registration.entering_phone, F.text)
async def enter_phone_text(message: Message, state: FSMContext) -> None:
    await handle_phone(message, state, message.text.strip())


async def handle_phone(message: Message, state: FSMContext, phone: str) -> None:
    invite = db.find_pending_invite(phone)
    if invite is not None:
        tg_full_name = message.from_user.full_name or message.from_user.first_name or str(message.from_user.id)
        user = db.claim_pending_invite(invite, message.from_user.id, phone, tg_full_name)
        await state.clear()
        await message.answer(
            f"✅ <b>Хуш келибсиз, {user['full_name']}!</b>\n\n"
            "Сиз админ томонидан тизимга қўшилгансиз — ҳисобингиз фаоллаштирилди.",
            reply_markup=menu_for(user),
            parse_mode="HTML",
        )
        return

    await state.update_data(phone=phone, user_id=message.from_user.id)
    await state.set_state(Registration.choosing_role)
    await message.answer(
        "👤 <b>Сиз ким сифатида рўйхатдан ўтасиз?</b>",
        reply_markup=role_choice_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(Registration.choosing_role, F.data.startswith("role:"))
async def choose_role(callback: CallbackQuery, state: FSMContext) -> None:
    role = callback.data.split(":", 1)[1]
    tg_user = callback.from_user
    full_name = tg_user.full_name or tg_user.first_name or str(tg_user.id)
    await state.update_data(role=role, full_name=full_name)
    await callback.message.edit_text(f"Сиз танладингиз: {ROLE_LABELS[role]}")
    await callback.answer()

    if role == "buyer":
        await state.set_state(Registration.entering_company_name)
        await callback.message.answer("Компаниянгиз номини киритинг:")
    else:
        await finish_registration(callback.message, state)


@router.message(Registration.entering_company_name, F.text)
async def enter_company_name(message: Message, state: FSMContext) -> None:
    await state.update_data(company_name=message.text.strip())
    await finish_registration(message, state)


async def finish_registration(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    role = data["role"]
    full_name = data["full_name"]
    company_name = data.get("company_name")
    phone = data["phone"]
    user_id = data.get("user_id") or message.from_user.id

    user = db.create_user(user_id, full_name, phone, role, company_name)
    await state.clear()

    if user["is_approved"]:
        await message.answer(
            f"🎉 <b>Рўйхатдан ўтиш якунланди!</b>\n\nХуш келибсиз, <b>{full_name}</b>.",
            reply_markup=menu_for(user),
            parse_mode="HTML",
        )
    else:
        await message.answer(
            "✅ <b>Рўйхатдан ўтдингиз!</b>\n\n⏳ Админ тасдиғини кутинг — тасдиқлангач сизга хабар берилади.",
            reply_markup=menu_for(user),
            parse_mode="HTML",
        )
        for admin_id in ADMIN_IDS:
            await message.bot.send_message(
                admin_id,
                f"🔔 <b>Янги фойдаланувчи тасдиқ кутмоқда</b>\n"
                f"─────────────────────\n"
                f"👤 Исми: <b>{full_name}</b>\n"
                f"🎭 Роли: <b>{ROLE_LABELS[role]}</b>\n"
                f"📱 Телефон: <b>{phone}</b>\n"
                f"🆔 ID: <code>{user['telegram_id']}</code>",
                parse_mode="HTML",
            )
