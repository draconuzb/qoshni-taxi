from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.session.get(User, user_id)

    async def create(self, telegram_id: int, full_name: str, phone: str) -> User:
        user = User(telegram_id=telegram_id, full_name=full_name, phone=phone)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_role(self, user_id: int, role: str) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(role=role)
        )
        await self.session.commit()

    async def block(self, user_id: int) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(is_blocked=True)
        )
        await self.session.commit()
