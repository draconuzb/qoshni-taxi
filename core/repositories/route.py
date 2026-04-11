from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.route import Route


class RouteRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active(self) -> list[Route]:
        result = await self.session.execute(
            select(Route).where(Route.is_active == True).order_by(Route.id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, route_id: int) -> Route | None:
        return await self.session.get(Route, route_id)

    async def create(self, from_name: str, to_name: str, price: int) -> Route:
        route = Route(from_name=from_name, to_name=to_name, price=price)
        self.session.add(route)
        await self.session.commit()
        await self.session.refresh(route)
        return route

    async def toggle_active(self, route_id: int) -> None:
        route = await self.session.get(Route, route_id)
        if route:
            route.is_active = not route.is_active
            await self.session.commit()
