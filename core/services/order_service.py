from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import OrderStatus
from core.models.order import Order
from core.repositories.order import OrderRepository
from core.repositories.driver import DriverRepository


class OrderService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.driver_repo = DriverRepository(session)

    async def create_order(
        self,
        user_id: int,
        route_id: int,
        passenger_count: int,
        price: int,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> Order:
        order = Order(
            user_id=user_id,
            route_id=route_id,
            passenger_count=passenger_count,
            price=price,
            pickup_latitude=latitude,
            pickup_longitude=longitude,
            status=OrderStatus.PENDING,
        )
        self.session.add(order)
        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def accept_order(self, order_id: int, driver_id: int) -> Order | None:
        order = await self.order_repo.get_by_id(order_id)
        if not order or order.status != OrderStatus.PENDING:
            return None

        order.driver_id = driver_id
        order.status = OrderStatus.ACCEPTED
        order.accepted_at = datetime.utcnow()
        await self.session.commit()
        return order

    async def update_status(self, order_id: int, status: OrderStatus) -> Order | None:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            return None

        order.status = status
        if status == OrderStatus.COMPLETED:
            order.completed_at = datetime.utcnow()
        await self.session.commit()
        return order

    async def cancel_order(self, order_id: int) -> Order | None:
        return await self.update_status(order_id, OrderStatus.CANCELLED)
