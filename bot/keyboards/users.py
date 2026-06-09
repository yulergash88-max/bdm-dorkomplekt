from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.common import ROLE_LABELS


def user_list_keyboard(users: list[dict], action_prefix: str) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{user['full_name']} ({ROLE_LABELS[user['role']]})",
                callback_data=f"{action_prefix}:{user['telegram_id']}",
            )
        ]
        for user in users
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def edit_field_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Исм-фамилия", callback_data=f"edit_field:{telegram_id}:full_name")],
            [InlineKeyboardButton(text="Телефон", callback_data=f"edit_field:{telegram_id}:phone")],
        ]
    )


def role_pick_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=ROLE_LABELS["supplier"], callback_data=f"set_role:{telegram_id}:supplier")],
            [InlineKeyboardButton(text=ROLE_LABELS["buyer"], callback_data=f"set_role:{telegram_id}:buyer")],
        ]
    )


def block_toggle_keyboard(telegram_id: int, is_blocked: bool) -> InlineKeyboardMarkup:
    label = "Блокдан чиқариш" if is_blocked else "Блоклаш"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"toggle_block:{telegram_id}")]
        ]
    )


def buyer_admin_toggle_keyboard(telegram_id: int, is_buyer_admin: bool) -> InlineKeyboardMarkup:
    label = "Харидор админлигидан олиш" if is_buyer_admin else "Харидор админи қилиш"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data=f"toggle_buyer_admin:{telegram_id}")]
        ]
    )


def add_user_role_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=ROLE_LABELS["supplier"], callback_data="add_user_role:supplier")],
            [InlineKeyboardButton(text=ROLE_LABELS["buyer"], callback_data="add_user_role:buyer")],
        ]
    )
