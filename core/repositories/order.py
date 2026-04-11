from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import OrderStatus
from core.models.order import Order


class OrderRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, order_id: int) -> Order | None:
        return await self.session.get(Order, order_id)

    async def get_active_by_user(self, user_id: int) -> list[Order]:
        result = await self.session.execute(
            select(Order)
            .where(Order.user_id == user_id)
            .where(Order.status.in_([OrderStatus.PENDING, OrderStatus.ACCEPTED, OrderStatus.IN_PROGRESS]))
            .order_by(Order.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_active_by_driver(self, driver_id: int) -> Order | None:
        result = await self.session.execute(
            select(Order)
            .where(Order.driver_id == driver_id)
            .where(Order.status.in_([OrderStatus.ACCEPTED, OrderStatus.DRIVER_ARRIVED, OrderStatus.IN_PROGRESS]))
            .order_by(Order.created_at.desc())
        )
        return result.scalar_first()

    async def get_pending_by_route(self, route_id: int) -> list[Order]:
        result = await self.session.execute(
            select(Order)
            .where(Order.route_id == route_id)
            .where(Order.status == OrderStatus.PENDING)
            .order_by(Order.created_at)
        )
        return list(result.scalars().all())
