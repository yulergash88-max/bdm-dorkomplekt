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
    return _deliveries_csv(deliveries, "yetkazib_berishlar.csv")


def deliveries_to_csv_by_date(deliveries: list[dict], date_from: str, date_to: str) -> BufferedInputFile:
    filename = f"hisobot_{date_from}__{date_to}.csv".replace("-", "")
    return _deliveries_csv(deliveries, filename)


def _deliveries_csv(deliveries: list[dict], filename: str) -> BufferedInputFile:
    header = [
        "№",
        "Товар",
        "Машина рақами",
        "Сана",
        "Ҳолат",
        "Юборилди (м³)",
        "Тортилди (т)",
        "Коэффициент",
        "Харидор куби (м³)",
        "Фарқ (м³)",
    ]
    rows = []
    for d in deliveries:
        raw_date = d.get("created_at") or ""
        try:
            from datetime import datetime
            date_str = datetime.fromisoformat(raw_date[:19]).strftime("%d.%m.%Y %H:%M")
        except (ValueError, TypeError):
            date_str = raw_date[:10]
        rows.append([
            d["id"],
            d.get("product_name") or "",
            d.get("car_number") or "",
            date_str,
            STATUS_LABELS.get(d["status"], d["status"]),
            d.get("supplier_kub") or "",
            d.get("buyer_tonnage") or "",
            d.get("lab_coefficient") or "",
            d.get("buyer_kub") or "",
            d.get("kub_difference") or "",
        ])
    return _to_csv_file(header, rows, filename)


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
