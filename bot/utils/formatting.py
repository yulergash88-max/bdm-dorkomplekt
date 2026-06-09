from collections import defaultdict

from bot.keyboards.common import ROLE_LABELS

STATUS_LABELS = {
    "new": "Янги",
    "sent_to_buyer": "Харидорга юборилди",
    "accepted": "Қабул қилинди",
    "weighed": "Тортилди",
    "completed": "Якунланди",
    "rejected": "Рад этилди",
}

STATUS_ICONS = {
    "new": "🆕",
    "sent_to_buyer": "📨",
    "accepted": "✅",
    "weighed": "⚖️",
    "completed": "🏁",
    "rejected": "❌",
}


def format_delivery(delivery: dict) -> str:
    status = delivery["status"]
    icon = STATUS_ICONS.get(status, "•")
    label = STATUS_LABELS.get(status, status)

    lines = [
        f"<b>📦 №{delivery['id']} — {delivery['product_name']}</b>",
        "─────────────────────",
        f"{icon} Ҳолат: <b>{label}</b>",
    ]

    if delivery.get("sale_datetime"):
        lines.append(f"🕐 Сана: <b>{delivery['sale_datetime']}</b>")
    if delivery.get("car_number"):
        lines.append(f"🚛 Машина: <b>{delivery['car_number']}</b>")

    lines.append(f"📐 Юборилди: <b>{delivery['supplier_kub']} м³</b>")

    if delivery.get("buyer_tonnage") is not None:
        lines.append(f"⚖️ Тортилди: <b>{delivery['buyer_tonnage']} т</b>")

    if delivery.get("lab_coefficient") is not None:
        lines.append(f"🔢 Коэффициент: <b>{delivery['lab_coefficient']}</b>")

    if delivery.get("buyer_kub") is not None:
        lines.append(f"📦 Харидор куби: <b>{delivery['buyer_kub']} м³</b>")

    if delivery.get("kub_difference") is not None:
        diff = delivery["kub_difference"]
        sign = "+" if diff > 0 else ""
        lines.append(f"📊 Фарқ: <b>{sign}{diff} м³</b>")

    return "\n".join(lines)


def format_user(user: dict) -> str:
    if user["is_blocked"]:
        status_icon, status_text = "⛔", "Блокланган"
    elif user["is_approved"]:
        status_icon, status_text = "✅", "Тасдиқланган"
    else:
        status_icon, status_text = "⏳", "Тасдиқ кутмоқда"

    role_text = ROLE_LABELS[user["role"]]
    if user["role"] == "buyer" and user.get("is_buyer_admin"):
        role_text += " 👑"

    lines = [
        f"<b>👤 {user['full_name']}</b>",
        "─────────────────────",
        f"🎭 Роль: <b>{role_text}</b>",
    ]
    if user["role"] == "buyer":
        lines.append(f"🏢 Компания: <b>{user.get('company_name') or '—'}</b>")

    lines += [
        f"📱 Телефон: <b>{user['phone'] or '—'}</b>",
        f"🆔 ID: <code>{user['telegram_id']}</code>",
        f"{status_icon} Ҳолат: <b>{status_text}</b>",
    ]
    return "\n".join(lines)


def format_date_report(deliveries: list[dict], date_from: str, date_to: str) -> str:
    if not deliveries:
        return (
            f"📊 <b>Ҳисобот: {date_from} — {date_to}</b>\n"
            "─────────────────────\n"
            "Bu davr uchun ma'lumot yo'q."
        )

    total = len(deliveries)
    by_status: dict[str, list] = defaultdict(list)
    for d in deliveries:
        by_status[d["status"]].append(d)

    lines = [
        f"📊 <b>Ҳисобот: {date_from} — {date_to}</b>",
        "─────────────────────",
        f"📦 Жами: <b>{total} та</b>",
        "",
    ]

    status_order = ["completed", "accepted", "sent_to_buyer", "weighed", "rejected", "new"]
    for status in status_order:
        if status not in by_status:
            continue
        items = by_status[status]
        icon = STATUS_ICONS.get(status, "•")
        label = STATUS_LABELS.get(status, status)
        completed_kub = sum(d["buyer_kub"] for d in items if d.get("buyer_kub"))
        supplier_kub = sum(d["supplier_kub"] for d in items if d.get("supplier_kub"))
        if status == "completed" and completed_kub:
            kub_str = f" | <b>{round(completed_kub, 2)} м³</b>"
        elif supplier_kub:
            kub_str = f" | <b>{round(supplier_kub, 2)} м³</b>"
        else:
            kub_str = ""
        lines.append(f"{icon} {label}: <b>{len(items)} та</b>{kub_str}")

    by_product: dict[str, dict] = defaultdict(lambda: {"count": 0, "kub": 0.0})
    for d in deliveries:
        name = d.get("product_name") or "Номаълум"
        by_product[name]["count"] += 1
        by_product[name]["kub"] += d.get("supplier_kub") or 0

    lines += ["", "─────────────────────", "📋 <b>Маҳсулотлар:</b>"]
    for name, data in sorted(by_product.items()):
        lines.append(f"  • {name}: <b>{data['count']} та</b> | {round(data['kub'], 2)} м³")

    return "\n".join(lines)
