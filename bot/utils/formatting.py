from bot.keyboards.common import ROLE_LABELS

STATUS_LABELS = {
    "new": "Янги (харидор тайинланмаган)",
    "sent_to_buyer": "Харидорга юборилди",
    "accepted": "Харидор қабул қилди",
    "weighed": "Тортилди (тонна киритилди)",
    "completed": "Якунланди",
    "rejected": "Рад этилди",
}


def format_delivery(delivery: dict) -> str:
    lines = [
        f"№{delivery['id']} — {delivery['product_name']}",
        f"Ҳолат: {STATUS_LABELS.get(delivery['status'], delivery['status'])}",
        f"Етказиб берувчи куби: {delivery['supplier_kub']}",
    ]
    if delivery.get("car_number"):
        lines.append(f"Машина: {delivery['car_number']}")

    if delivery.get("buyer_tonnage") is not None:
        lines.append(f"Харидор тортган тонна: {delivery['buyer_tonnage']}")

    if delivery.get("lab_coefficient") is not None:
        lines.append(f"Лаборатория коэффициенти: {delivery['lab_coefficient']}")

    if delivery.get("buyer_kub") is not None:
        lines.append(f"Харидор куби (ҳисобланган): {delivery['buyer_kub']}")

    if delivery.get("kub_difference") is not None:
        diff = delivery["kub_difference"]
        sign = "+" if diff > 0 else ""
        lines.append(f"Фарқ (харидор − етказиб берувчи): {sign}{diff}")

    return "\n".join(lines)


def format_user(user: dict) -> str:
    if user["is_blocked"]:
        status = "Блокланган ⛔"
    elif user["is_approved"]:
        status = "Тасдиқланган ✅"
    else:
        status = "Тасдиқ кутмоқда ⏳"

    role_line = ROLE_LABELS[user["role"]]
    if user["role"] == "buyer" and user.get("is_buyer_admin"):
        role_line += " — Харидор админи 👑"

    lines = [
        f"Исми: {user['full_name']}",
        f"Роли: {role_line}",
    ]
    if user["role"] == "buyer":
        lines.append(f"Компания: {user.get('company_name') or '—'}")

    lines += [
        f"Телефон: {user['phone'] or '—'}",
        f"ID: {user['telegram_id']}",
        f"Ҳолат: {status}",
    ]
    return "\n".join(lines)
