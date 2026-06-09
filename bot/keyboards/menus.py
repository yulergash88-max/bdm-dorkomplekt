from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

SUPPLIER_NEW_DELIVERY = "Янги етказиб бериш"
SUPPLIER_MY_DELIVERIES = "Менинг етказиб беришларим"

BUYER_PENDING = "Кутилаётган етказиб беришлар"
BUYER_HISTORY = "Тарих"

ADMIN_PENDING_USERS = "Тасдиқ кутаётган фойдаланувчилар"
ADMIN_UNASSIGNED = "Харидор тайинланмаган етказиб беришлар"
ADMIN_ALL_DELIVERIES = "Барча етказиб беришлар"
ADMIN_USERS_SECTION = "Фойдаланувчилар бошқаруви"
ADMIN_REPORTS_SECTION = "Ҳисоботлар"
BACK_TO_ADMIN_MENU = "⬅️ Орқага"

ADMIN_ADD_USER = "Янги фойдаланувчи қўшиш"
ADMIN_LIST_USERS = "Барча фойдаланувчилар"
ADMIN_EDIT_USER = "Фойдаланувчини таҳрирлаш"
ADMIN_CHANGE_ROLE = "Ролни ўзгартириш"
ADMIN_BLOCK_USER = "Блоклаш / блокдан чиқариш"
ADMIN_TOGGLE_BUYER_ADMIN = "Харидор админи қилиш / олиб ташлаш"
ADMIN_TOGGLE_WEIGHING = "⚖️ Тарози белгисини ўзгартириш"

BUYER_COMPANY_REPORT = "Компания ҳисоботи"
BUYER_DATE_REPORT = "📊 Ҳисобот (сана бўйича)"
SUPPLIER_DATE_REPORT = "📊 Ҳисобот (сана бўйича)"

ADMIN_COEFFICIENT = "Коэффициент созламаси ⚙️"
ADMIN_PRODUCTS = "Махсулот коэффициентлари 📋"
ADMIN_REPORT_DELIVERY_STATS = "Етказиб бериш статистикаси"
ADMIN_REPORT_USER_ACTIVITY = "Фойдаланувчилар фаолияти"


def supplier_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=SUPPLIER_MY_DELIVERIES)],
            [KeyboardButton(text=SUPPLIER_DATE_REPORT)],
        ],
        resize_keyboard=True,
    )


def buyer_menu(is_buyer_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=BUYER_PENDING)],
        [KeyboardButton(text=BUYER_HISTORY)],
        [KeyboardButton(text=BUYER_DATE_REPORT)],
    ]
    if is_buyer_admin:
        keyboard.append([KeyboardButton(text=BUYER_COMPANY_REPORT)])

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADMIN_PENDING_USERS)],
            [KeyboardButton(text=ADMIN_UNASSIGNED)],
            [KeyboardButton(text=ADMIN_ALL_DELIVERIES)],
            [KeyboardButton(text=ADMIN_USERS_SECTION)],
            [KeyboardButton(text=ADMIN_REPORTS_SECTION)],
            [KeyboardButton(text=ADMIN_PRODUCTS)],
            [KeyboardButton(text=ADMIN_COEFFICIENT)],
        ],
        resize_keyboard=True,
    )


def admin_users_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADMIN_ADD_USER)],
            [KeyboardButton(text=ADMIN_LIST_USERS)],
            [KeyboardButton(text=ADMIN_EDIT_USER)],
            [KeyboardButton(text=ADMIN_CHANGE_ROLE)],
            [KeyboardButton(text=ADMIN_BLOCK_USER)],
            [KeyboardButton(text=ADMIN_TOGGLE_BUYER_ADMIN)],
            [KeyboardButton(text=ADMIN_TOGGLE_WEIGHING)],
            [KeyboardButton(text=BACK_TO_ADMIN_MENU)],
        ],
        resize_keyboard=True,
    )


def admin_reports_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADMIN_REPORT_DELIVERY_STATS)],
            [KeyboardButton(text=ADMIN_REPORT_USER_ACTIVITY)],
            [KeyboardButton(text=BACK_TO_ADMIN_MENU)],
        ],
        resize_keyboard=True,
    )
