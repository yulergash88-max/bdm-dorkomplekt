from collections import defaultdict

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


def format_date_report(deliveries: list[dict], date_from: str, date_to: str) -> str:
    if not deliveries:
        return f"📊 <b>{date_from} — {date_to}</b>\n\nБу давр учун маълумот йўқ."

    total = len(deliveries)
    by_status: dict[str, list] = defaultdict(list)
    for d in deliveries:
        by_status[d["status"]].append(d)

    status_icons = {
        "completed": "✅",
        "rejected": "❌",
        "accepted": "🔄",
        "sent_to_buyer": "📨",
        "new": "🆕",
        "weighed": "⚖️",
    }

    lines = [f"📊 <b>Ҳисобот: {date_from} — {date_to}</b>", f"Жами: <b>{total} та</b>", ""]

    for status, items in sorted(by_status.items(), key=lambda x: x[0]):
        icon = status_icons.get(status, "•")
        label = STATUS_LABELS.get(status, status)
        completed_kub = sum(d["buyer_kub"] for d in items if d.get("buyer_kub"))
        supplier_kub = sum(d["supplier_kub"] for d in items if d.get("supplier_kub"))
        kub_str = ""
        if status == "completed":
            kub_str = f" | Харидор куби: <b>{round(completed_kub, 2)} м³</b>"
        elif supplier_kub:
            kub_str = f" | <b>{round(supplier_kub, 2)} м³</b>"
        lines.append(f"{icon} {label}: <b>{len(items)} та</b>{kub_str}")

    by_product: dict[str, dict] = defaultdict(lambda: {"count": 0, "kub": 0.0})
    for d in deliveries:
        name = d.get("product_name") or "Номаълум"
        by_product[name]["count"] += 1
        by_product[name]["kub"] += d.get("supplier_kub") or 0

    lines += ["", "📦 <b>Маҳсулотлар:</b>"]
    for name, data in sorted(by_product.items()):
        lines.append(f"  • {name}: {data['count']} та | {round(data['kub'], 2)} м³")

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
