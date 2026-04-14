import math

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.enums import DriverStatus, TripStatus, UserRole
from core.models import Driver, Route, Trip, Booking, UserRoute
from core.models.user import User
from webapp.deps import get_session, templates, PAGE_SIZE

router = APIRouter()


class DriverUpdate(BaseModel):
    car_model: str | None = Field(default=None, max_length=100)
    car_color: str | None = Field(default=None, max_length=50)
    license_plate: str | None = Field(default=None, max_length=20)


@router.get("/drivers", response_class=HTMLResponse)
async def drivers_page(request: Request, filter: str = "all", page: int = 1, session: AsyncSession = Depends(get_session)):
    query = select(Driver, User).join(User, Driver.user_id == User.id)
    if filter == "verified":
        query = query.where(Driver.status == DriverStatus.VERIFIED)
    elif filter == "blocked":
        query = query.where(Driver.status == DriverStatus.BLOCKED)

    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    result = await session.execute(
        query.order_by(Driver.created_at.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    )
    rows = result.all()

    return templates.TemplateResponse(request, "drivers.html", {
        "drivers": rows, "filter": filter, "page": page, "total_pages": total_pages,
        "total": total, "pending_count": 0,
    })


@router.get("/drivers/{driver_id}", response_class=HTMLResponse)
async def driver_detail(request: Request, driver_id: int, session: AsyncSession = Depends(get_session)):
    driver = await session.get(Driver, driver_id)
    if not driver:
        raise HTTPException(404)
    user = await session.get(User, driver.user_id)

    orders_count = await session.scalar(select(func.count(Trip.id)).where(Trip.driver_id == driver_id)) or 0
    completed = await session.scalar(
        select(func.count(Trip.id)).where(and_(Trip.driver_id == driver_id, Trip.status == TripStatus.DEPARTED))
    ) or 0
    revenue = await session.scalar(
        select(func.coalesce(func.sum(Trip.price_per_seat * Trip.booked_seats), 0))
        .where(and_(Trip.driver_id == driver_id, Trip.status == TripStatus.DEPARTED))
    ) or 0

    fav_result = await session.execute(
        select(UserRoute).where(UserRoute.user_id == driver.user_id).options(selectinload(UserRoute.route))
    )
    routes = [fr.route for fr in fav_result.scalars().all()]
    all_routes = (await session.execute(select(Route).where(Route.is_active == True).order_by(Route.id))).scalars().all()

    result = await session.execute(
        select(Trip).where(Trip.driver_id == driver_id)
        .options(selectinload(Trip.route)).order_by(Trip.created_at.desc()).limit(10)
    )
    recent_orders = result.scalars().all()

    return templates.TemplateResponse(request, "driver_detail.html", {
        "driver": driver, "user": user, "routes": routes, "all_routes": all_routes,
        "orders_count": orders_count, "completed": completed, "revenue": revenue,
        "recent_orders": recent_orders,
    })


async def _set_status(driver_id: int, status: DriverStatus, session: AsyncSession) -> dict:
    driver = await session.get(Driver, driver_id)
    if not driver:
        raise HTTPException(404)
    driver.status = status
    await session.commit()
    return {"ok": True}


@router.post("/api/drivers/{driver_id}/verify")
async def api_verify_driver(driver_id: int, session: AsyncSession = Depends(get_session)):
    return await _set_status(driver_id, DriverStatus.VERIFIED, session)


@router.post("/api/drivers/{driver_id}/reject")
async def api_reject_driver(driver_id: int, session: AsyncSession = Depends(get_session)):
    return await _set_status(driver_id, DriverStatus.BLOCKED, session)


@router.post("/api/drivers/{driver_id}/block")
async def api_block_driver(driver_id: int, session: AsyncSession = Depends(get_session)):
    return await _set_status(driver_id, DriverStatus.BLOCKED, session)


@router.post("/api/drivers/{driver_id}/unblock")
async def api_unblock_driver(driver_id: int, session: AsyncSession = Depends(get_session)):
    return await _set_status(driver_id, DriverStatus.VERIFIED, session)


@router.delete("/api/drivers/{driver_id}")
async def api_delete_driver(driver_id: int, session: AsyncSession = Depends(get_session)):
    driver = await session.get(Driver, driver_id)
    if not driver:
        raise HTTPException(404)
    trips = (await session.execute(select(Trip).where(Trip.driver_id == driver.id))).scalars().all()
    for trip in trips:
        await session.execute(Booking.__table__.delete().where(Booking.trip_id == trip.id))
        await session.delete(trip)
    user = await session.get(User, driver.user_id)
    if user:
        user.role = UserRole.USER
    await session.delete(driver)
    await session.commit()
    return {"ok": True}


@router.post("/api/drivers/{driver_id}/update")
async def api_update_driver(
    driver_id: int,
    data: DriverUpdate,
    session: AsyncSession = Depends(get_session),
):
    driver = await session.get(Driver, driver_id)
    if not driver:
        raise HTTPException(404)
    if data.car_model is not None:
        driver.car_model = data.car_model
    if data.car_color is not None:
        driver.car_color = data.car_color
    if data.license_plate is not None:
        driver.license_plate = data.license_plate
    await session.commit()
    return {"ok": True}
