from aiogram import types
from aiogram.filters import BaseFilter

from bot.database import db


class require_role(BaseFilter):
    """Allows the message through only for approved users with the given role."""

    def __init__(self, role: str) -> None:
        self.role = role

    async def __call__(self, message: types.Message) -> bool:
        user = db.get_user(message.from_user.id)
        return bool(
            user
            and user["role"] == self.role
            and user["is_approved"]
            and not user["is_blocked"]
        )


class require_admin(BaseFilter):
    def __init__(self, admin_ids: set[int]) -> None:
        self.admin_ids = admin_ids

    async def __call__(self, message: types.Message) -> bool:
        return message.from_user.id in self.admin_ids
