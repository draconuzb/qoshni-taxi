from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.enums import DriverStatus
from core.models.driver import Driver


class DriverRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user_id(self, user_id: int) -> Driver | None:
        result = await self.session.execute(
            select(Driver).where(Driver.user_id == user_id).options(selectinload(Driver.routes))
        )
        return result.scalar_one_or_none()

    async def get_online_for_route(self, route_id: int) -> list[Driver]:
        result = await self.session.execute(
            select(Driver)
            .where(Driver.is_online == True)
            .where(Driver.status == DriverStatus.VERIFIED)
            .where(Driver.routes.any(id=route_id))
            .options(selectinload(Driver.routes))
        )
        return list(result.scalars().all())

    async def get_pending_verification(self) -> list[Driver]:
        result = await self.session.execute(
            select(Driver).where(Driver.status == DriverStatus.PENDING_VERIFICATION)
        )
        return list(result.scalars().all())
