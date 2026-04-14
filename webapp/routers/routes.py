import math

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field, conint
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import TripStatus
from core.models import Route, Trip, UserRoute
from core.locations import REGIONS
from webapp.deps import get_session, templates, PAGE_SIZE

router = APIRouter()


class RouteCreate(BaseModel):
    name: str = Field(default="", max_length=100)
    region: str = Field(default="", max_length=50)
    district: str = Field(default="", max_length=50)
    from_name: str = Field(min_length=1, max_length=255)
    to_name: str = Field(min_length=1, max_length=255)
    price: conint(ge=0, le=100_000_000)


class RoutePriceUpdate(BaseModel):
    price: conint(ge=0, le=100_000_000)


@router.get("/routes", response_class=HTMLResponse)
async def routes_page(request: Request, page: int = 1, session: AsyncSession = Depends(get_session)):
    total = await session.scalar(select(func.count(Route.id))) or 0
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    result = await session.execute(
        select(Route).order_by(Route.id).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    )
    routes = result.scalars().all()

    route_stats: dict[int, dict] = {}
    for route in routes:
        trips_count = await session.scalar(
            select(func.count(Trip.id)).where(Trip.route_id == route.id)
        ) or 0
        completed = await session.scalar(
            select(func.count(Trip.id)).where(and_(Trip.route_id == route.id, Trip.status == TripStatus.DEPARTED))
        ) or 0
        revenue = await session.scalar(
            select(func.coalesce(func.sum(Trip.price_per_seat * Trip.booked_seats), 0))
            .where(and_(Trip.route_id == route.id, Trip.status == TripStatus.DEPARTED))
        ) or 0
        driver_count = await session.scalar(
            select(func.count(UserRoute.id)).where(UserRoute.route_id == route.id)
        ) or 0
        route_stats[route.id] = {
            "orders": trips_count, "completed": completed,
            "revenue": revenue, "drivers": driver_count,
        }

    return templates.TemplateResponse(request, "routes.html", {
        "routes": routes, "route_stats": route_stats,
        "page": page, "total_pages": total_pages, "total": total,
    })


@router.get("/api/locations/regions")
async def api_regions():
    return [{"id": k, "name": v["name"]} for k, v in REGIONS.items()]


@router.get("/api/locations/districts/{region_id}")
async def api_districts(region_id: str):
    region = REGIONS.get(region_id)
    if not region:
        raise HTTPException(404)
    return [{"id": k, "name": v} for k, v in region["districts"].items()]


@router.post("/api/routes", response_class=JSONResponse)
async def api_create_route(data: RouteCreate, session: AsyncSession = Depends(get_session)):
    route = Route(**data.model_dump())
    session.add(route)
    await session.commit()
    return {"ok": True, "id": route.id}


@router.post("/api/routes/{route_id}/toggle")
async def api_toggle_route(route_id: int, session: AsyncSession = Depends(get_session)):
    route = await session.get(Route, route_id)
    if not route:
        raise HTTPException(404)
    route.is_active = not route.is_active
    await session.commit()
    return {"ok": True, "is_active": route.is_active}


@router.post("/api/routes/{route_id}/price")
async def api_update_price(route_id: int, data: RoutePriceUpdate, session: AsyncSession = Depends(get_session)):
    route = await session.get(Route, route_id)
    if not route:
        raise HTTPException(404)
    route.price = data.price
    await session.commit()
    return {"ok": True}


@router.delete("/api/routes/{route_id}")
async def api_delete_route(route_id: int, session: AsyncSession = Depends(get_session)):
    route = await session.get(Route, route_id)
    if not route:
        raise HTTPException(404)
    await session.delete(route)
    await session.commit()
    return {"ok": True}
