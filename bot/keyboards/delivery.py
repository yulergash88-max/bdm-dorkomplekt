from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def assign_buyer_keyboard(delivery_id: int, buyers: list[dict]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=buyer["full_name"],
                callback_data=f"assign:{delivery_id}:{buyer['telegram_id']}",
            )
        ]
        for buyer in buyers
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def accept_reject_keyboard(delivery_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Қабул қилиш", callback_data=f"accept:{delivery_id}"),
                InlineKeyboardButton(text="Рад этиш", callback_data=f"reject:{delivery_id}"),
            ]
        ]
    )


def buyer_weigh_keyboard(delivery_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚖️ Тарозига тортаман", callback_data=f"buyer_weigh:{delivery_id}")],
            [InlineKeyboardButton(text="📐 Етказиб берувчи куби билан", callback_data=f"buyer_noweigh:{delivery_id}")],
        ]
    )


def approve_user_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Тасдиқлаш", callback_data=f"approve_user:{telegram_id}")]
        ]
    )
