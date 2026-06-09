import csv
import io

from aiogram.types import BufferedInputFile

from bot.keyboards.common import ROLE_LABELS
from bot.utils.formatting import STATUS_LABELS


def _to_csv_file(header: list[str], rows: list[list], filename: str) -> BufferedInputFile:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    writer.writerows(rows)
    return BufferedInputFile(buffer.getvalue().encode("utf-8-sig"), filename=filename)


def deliveries_to_csv(deliveries: list[dict]) -> BufferedInputFile:
    header = [
        "ID",
        "Маҳсулот",
        "Ҳолат",
        "Етказиб берувчи куби",
        "Харидор тортган тонна",
        "Лаборатория коэффициенти",
        "Харидор куби",
        "Куб фарқи",
        "Яратилган сана",
    ]
    rows = [
        [
            delivery["id"],
            delivery["product_name"],
            STATUS_LABELS.get(delivery["status"], delivery["status"]),
            delivery["supplier_kub"],
            delivery["buyer_tonnage"],
            delivery["lab_coefficient"],
            delivery["buyer_kub"],
            delivery["kub_difference"],
            delivery["created_at"],
        ]
        for delivery in deliveries
    ]
    return _to_csv_file(header, rows, "yetkazib_berishlar.csv")


def users_to_csv(users: list[dict]) -> BufferedInputFile:
    header = ["Telegram ID", "Исм-фамилия", "Роли", "Телефон", "Тасдиқланган", "Блокланган", "Яратилган сана"]
    rows = [
        [
            user["telegram_id"],
            user["full_name"],
            ROLE_LABELS[user["role"]],
            user["phone"] or "",
            "ҳа" if user["is_approved"] else "йўқ",
            "ҳа" if user["is_blocked"] else "йўқ",
            user["created_at"],
        ]
        for user in users
    ]
    return _to_csv_file(header, rows, "foydalanuvchilar.csv")
