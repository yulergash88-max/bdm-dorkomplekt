from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

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
