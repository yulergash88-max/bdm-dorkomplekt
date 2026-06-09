from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

CANCEL_BTN = "❌ Бекор"
MANUAL_DATE_BTN = "✏️ Ўзим киритаман"
MANUAL_NUM_BTN = "✏️ Бошқа рақам"

DATE_TODAY = "📅 Бугун"
DATE_YESTERDAY = "📅 Кеча"
DATE_THIS_MONTH = "📅 Бу ой"
DATE_LAST_MONTH = "📅 Олдинги ой"

DATE_PRESETS = {DATE_TODAY, DATE_YESTERDAY, DATE_THIS_MONTH, DATE_LAST_MONTH}


def tonnage_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="5"), KeyboardButton(text="10"), KeyboardButton(text="15")],
            [KeyboardButton(text="20"), KeyboardButton(text="25"), KeyboardButton(text="30")],
            [KeyboardButton(text="35"), KeyboardButton(text="40"), KeyboardButton(text="50")],
            [KeyboardButton(text=MANUAL_NUM_BTN)],
            [KeyboardButton(text=CANCEL_BTN)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def manual_number_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_BTN)]],
        resize_keyboard=True,
    )


def numpad_keyboard(current: str, delivery_id: int) -> InlineKeyboardMarkup:
    """Inline numpad for tonnage entry. current is the value being built."""
    display = current if current else "0"

    def btn(text: str, action: str) -> InlineKeyboardButton:
        return InlineKeyboardButton(text=text, callback_data=f"np:{delivery_id}:{action}")

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⚖️  {display}  т", callback_data="np_noop")],
        [btn("1", "1"), btn("2", "2"), btn("3", "3")],
        [btn("4", "4"), btn("5", "5"), btn("6", "6")],
        [btn("7", "7"), btn("8", "8"), btn("9", "9")],
        [btn(".", "."), btn("0", "0"), btn("⌫", "del")],
        [btn("✅ Тасдиқлаш", "ok")],
        [btn("❌ Бекор", "cancel")],
    ])


def confirm_tonnage_keyboard(tonnage: str, delivery_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Ҳа, {tonnage} тонна", callback_data=f"np:{delivery_id}:confirm")],
        [InlineKeyboardButton(text="✏️ Ўзгартириш", callback_data=f"np:{delivery_id}:redo")],
    ])


def date_range_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=DATE_TODAY), KeyboardButton(text=DATE_YESTERDAY)],
            [KeyboardButton(text=DATE_THIS_MONTH), KeyboardButton(text=DATE_LAST_MONTH)],
            [KeyboardButton(text=MANUAL_DATE_BTN)],
            [KeyboardButton(text=CANCEL_BTN)],
        ],
        resize_keyboard=True,
    )


def manual_date_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=CANCEL_BTN)]],
        resize_keyboard=True,
    )
