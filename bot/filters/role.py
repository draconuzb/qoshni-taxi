from aiogram.filters import BaseFilter
from aiogram.types import Message

from core.enums import UserRole
from core.models.user import User


class RoleFilter(BaseFilter):
    """Foydalanuvchi rolini tekshirish filtri."""

    def __init__(self, role: UserRole | list[UserRole]):
        self.roles = [role] if isinstance(role, UserRole) else role

    async def __call__(self, message: Message, db_user: User | None = None) -> bool:
        if not db_user:
            return False
        return db_user.role in self.roles
