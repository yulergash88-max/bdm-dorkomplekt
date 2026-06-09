from bot.keyboards.common import ROLE_LABELS
from bot.utils.formatting import STATUS_LABELS


def build_delivery_stats(deliveries: list[dict]) -> dict:
    counts = {status: 0 for status in STATUS_LABELS}
    supplier_kub_total = 0.0
    buyer_kub_total = 0.0
    kub_difference_total = 0.0
    completed_count = 0

    for delivery in deliveries:
        counts[delivery["status"]] = counts.get(delivery["status"], 0) + 1
        supplier_kub_total += float(delivery["supplier_kub"] or 0)

        if delivery["status"] == "completed":
            completed_count += 1
            buyer_kub_total += float(delivery["buyer_kub"] or 0)
            kub_difference_total += float(delivery["kub_difference"] or 0)

    return {
        "total": len(deliveries),
        "counts": counts,
        "supplier_kub_total": round(supplier_kub_total, 3),
        "buyer_kub_total": round(buyer_kub_total, 3),
        "kub_difference_total": round(kub_difference_total, 3),
        "completed_count": completed_count,
    }


def format_delivery_stats(stats: dict) -> str:
    lines = [f"Жами етказиб беришлар: {stats['total']}", ""]

    for status, label in STATUS_LABELS.items():
        lines.append(f"{label}: {stats['counts'].get(status, 0)}")

    lines += [
        "",
        f"Етказиб берувчи куби (жами): {stats['supplier_kub_total']}",
        f"Якунланганлар сони: {stats['completed_count']}",
        f"Харидор куби (якунланганлар бўйича жами): {stats['buyer_kub_total']}",
        f"Куб фарқи (якунланганлар бўйича жами): {stats['kub_difference_total']}",
    ]
    return "\n".join(lines)


def build_user_activity(users: list[dict], deliveries: list[dict]) -> list[dict]:
    delivery_counts: dict[int, dict[str, int]] = {}
    for delivery in deliveries:
        supplier_id = delivery["supplier_id"]
        delivery_counts.setdefault(supplier_id, {"created": 0, "handled": 0})
        delivery_counts[supplier_id]["created"] += 1

        buyer_id = delivery["buyer_id"]
        if buyer_id is not None:
            delivery_counts.setdefault(buyer_id, {"created": 0, "handled": 0})
            delivery_counts[buyer_id]["handled"] += 1

    rows = []
    for user in users:
        counts = delivery_counts.get(user["telegram_id"], {"created": 0, "handled": 0})
        rows.append(
            {
                "full_name": user["full_name"],
                "role": user["role"],
                "is_approved": user["is_approved"],
                "is_blocked": user["is_blocked"],
                "created": counts["created"],
                "handled": counts["handled"],
            }
        )
    return rows


def format_user_activity(rows: list[dict]) -> str:
    lines = []
    for row in rows:
        if row["is_blocked"]:
            status = "блокланган"
        elif not row["is_approved"]:
            status = "тасдиқланмаган"
        else:
            status = "фаол"

        lines.append(
            f"{row['full_name']} ({ROLE_LABELS[row['role']]}, {status}) — "
            f"яратган: {row['created']}, кўриб чиққан: {row['handled']}"
        )
    return "\n".join(lines)
