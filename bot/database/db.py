from supabase import Client, create_client

from bot.config import SUPABASE_KEY, SUPABASE_URL
from bot.utils.phone import normalize_phone

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# --- users ---------------------------------------------------------------

def get_user(telegram_id: int) -> dict | None:
    result = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
    return result.data[0] if result.data else None


def create_user(telegram_id: int, full_name: str, phone: str, role: str, company_name: str | None = None) -> dict:
    is_approved = role == "buyer"  # suppliers/admins are approved manually by an admin
    result = (
        supabase.table("users")
        .insert(
            {
                "telegram_id": telegram_id,
                "full_name": full_name,
                "phone": phone,
                "role": role,
                "company_name": company_name,
                "is_approved": is_approved,
            }
        )
        .execute()
    )
    return result.data[0]


def approve_user(telegram_id: int) -> None:
    supabase.table("users").update({"is_approved": True}).eq("telegram_id", telegram_id).execute()


def list_users_by_role(role: str) -> list[dict]:
    result = supabase.table("users").select("*").eq("role", role).execute()
    return result.data


def list_pending_users() -> list[dict]:
    result = supabase.table("users").select("*").eq("is_approved", False).execute()
    return result.data


def update_user(telegram_id: int, **fields) -> None:
    supabase.table("users").update(fields).eq("telegram_id", telegram_id).execute()


def block_user(telegram_id: int) -> None:
    supabase.table("users").update({"is_blocked": True}).eq("telegram_id", telegram_id).execute()


def unblock_user(telegram_id: int) -> None:
    supabase.table("users").update({"is_blocked": False}).eq("telegram_id", telegram_id).execute()


def list_all_users() -> list[dict]:
    result = supabase.table("users").select("*").order("created_at", desc=True).execute()
    return result.data


def create_user_by_admin(
    telegram_id: int, full_name: str, phone: str, role: str, company_name: str | None = None
) -> dict:
    """Admin-added users are pre-approved — the admin is vouching for them directly."""
    result = (
        supabase.table("users")
        .insert(
            {
                "telegram_id": telegram_id,
                "full_name": full_name,
                "phone": phone,
                "role": role,
                "company_name": company_name,
                "is_approved": True,
            }
        )
        .execute()
    )
    return result.data[0]


def create_pending_invite(phone: str, role: str, company_name: str | None = None) -> dict:
    """Holds an admin-added user without a known Telegram ID until they claim it via /start."""
    result = (
        supabase.table("pending_invites")
        .insert(
            {
                "phone": phone,
                "normalized_phone": normalize_phone(phone),
                "full_name": None,
                "role": role,
                "company_name": company_name,
            }
        )
        .execute()
    )
    return result.data[0]


def find_pending_invite(phone: str) -> dict | None:
    result = (
        supabase.table("pending_invites")
        .select("*")
        .eq("normalized_phone", normalize_phone(phone))
        .execute()
    )
    return result.data[0] if result.data else None


def claim_pending_invite(invite: dict, telegram_id: int, phone: str, tg_full_name: str) -> dict:
    """Turns a pending invite into a real (pre-approved) user once its phone is confirmed via /start."""
    user = create_user_by_admin(
        telegram_id, tg_full_name, phone, invite["role"], invite.get("company_name")
    )
    supabase.table("pending_invites").delete().eq("id", invite["id"]).execute()
    return user


def find_buyer_company(client_name: str) -> list[dict]:
    """Returns active buyer-role users whose company_name matches client_name (case-insensitive)."""
    result = (
        supabase.table("users")
        .select("*")
        .eq("role", "buyer")
        .eq("is_approved", True)
        .eq("is_blocked", False)
        .ilike("company_name", client_name.strip())
        .execute()
    )
    return result.data


def ensure_system_supplier(telegram_id: int, full_name: str) -> None:
    """Creates the synthetic supplier used for sales-feed auto-created deliveries, if missing."""
    if get_user(telegram_id) is not None:
        return

    supabase.table("users").insert(
        {
            "telegram_id": telegram_id,
            "full_name": full_name,
            "phone": None,
            "role": "supplier",
            "is_approved": True,
        }
    ).execute()


# --- deliveries -----------------------------------------------------------

def create_delivery(supplier_id: int, product_name: str, supplier_kub: float) -> dict:
    result = (
        supabase.table("deliveries")
        .insert(
            {
                "supplier_id": supplier_id,
                "product_name": product_name,
                "supplier_kub": supplier_kub,
                "status": "new",
            }
        )
        .execute()
    )
    return result.data[0]


def get_delivery(delivery_id: int) -> dict | None:
    result = supabase.table("deliveries").select("*").eq("id", delivery_id).execute()
    return result.data[0] if result.data else None


def assign_buyer(delivery_id: int, buyer_id: int) -> None:
    supabase.table("deliveries").update(
        {"buyer_id": buyer_id, "status": "sent_to_buyer"}
    ).eq("id", delivery_id).execute()


def accept_delivery(delivery_id: int) -> None:
    supabase.table("deliveries").update({"status": "accepted"}).eq("id", delivery_id).execute()


def reject_delivery(delivery_id: int) -> None:
    supabase.table("deliveries").update({"status": "rejected"}).eq("id", delivery_id).execute()


def set_buyer_tonnage(delivery_id: int, tonnage: float) -> None:
    supabase.table("deliveries").update(
        {"buyer_tonnage": tonnage, "status": "weighed"}
    ).eq("id", delivery_id).execute()


def complete_delivery(delivery_id: int, lab_coefficient: float, buyer_kub: float, kub_difference: float) -> None:
    supabase.table("deliveries").update(
        {
            "lab_coefficient": lab_coefficient,
            "buyer_kub": buyer_kub,
            "kub_difference": kub_difference,
            "status": "completed",
        }
    ).eq("id", delivery_id).execute()


def list_deliveries_by_supplier(supplier_id: int) -> list[dict]:
    result = (
        supabase.table("deliveries")
        .select("*")
        .eq("supplier_id", supplier_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


def list_deliveries_by_buyer(buyer_id: int, status: str | None = None) -> list[dict]:
    query = supabase.table("deliveries").select("*").eq("buyer_id", buyer_id)
    if status:
        query = query.eq("status", status)
    result = query.order("created_at", desc=True).execute()
    return result.data


def list_unassigned_deliveries() -> list[dict]:
    result = (
        supabase.table("deliveries")
        .select("*")
        .eq("status", "new")
        .order("created_at")
        .execute()
    )
    return result.data


def get_setting(key: str) -> str | None:
    result = supabase.table("settings").select("value").eq("key", key).execute()
    return result.data[0]["value"] if result.data else None


def set_setting(key: str, value: str) -> None:
    supabase.table("settings").upsert({"key": key, "value": value, "updated_at": "now()"}).execute()


def list_deliveries_by_status(status: str) -> list[dict]:
    result = (
        supabase.table("deliveries")
        .select("*")
        .eq("status", status)
        .order("created_at")
        .execute()
    )
    return result.data


def list_all_deliveries() -> list[dict]:
    result = supabase.table("deliveries").select("*").order("created_at", desc=True).execute()
    return result.data


def list_company_buyers(company_name: str) -> list[dict]:
    result = (
        supabase.table("users")
        .select("*")
        .eq("role", "buyer")
        .eq("company_name", company_name)
        .execute()
    )
    return result.data


def list_deliveries_by_company(company_name: str, status: str | None = None) -> list[dict]:
    member_ids = [user["telegram_id"] for user in list_company_buyers(company_name)]
    if not member_ids:
        return []

    query = supabase.table("deliveries").select("*").in_("buyer_id", member_ids)
    if status:
        query = query.eq("status", status)
    result = query.order("created_at", desc=True).execute()
    return result.data
