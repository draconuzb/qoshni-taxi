from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from core.enums import TripStatus
from core.models import Driver, Route, Trip, Booking
from core.models.user import User
from webapp.deps import get_session, templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    departed_today = and_(Trip.status == TripStatus.DEPARTED, Trip.departed_at >= today_start)
    departed_all = Trip.status == TripStatus.DEPARTED

    total_users = await session.scalar(select(func.count(User.id))) or 0
    total_drivers = await session.scalar(select(func.count(Driver.id))) or 0
    today_orders = await session.scalar(select(func.count(Booking.id)).where(Booking.created_at >= today_start)) or 0
    today_departed = await session.scalar(select(func.count(Trip.id)).where(departed_today)) or 0
    today_revenue = await session.scalar(
        select(func.coalesce(func.sum(Trip.price_per_seat * Trip.booked_seats), 0)).where(departed_today)
    ) or 0
    active_trips = await session.scalar(select(func.count(Trip.id)).where(Trip.status == TripStatus.COLLECTING)) or 0
    total_orders = await session.scalar(select(func.count(Booking.id))) or 0
    total_departed = await session.scalar(select(func.count(Trip.id)).where(departed_all)) or 0
    total_revenue = await session.scalar(
        select(func.coalesce(func.sum(Trip.price_per_seat * Trip.booked_seats), 0)).where(departed_all)
    ) or 0
    total_trips = await session.scalar(select(func.count(Trip.id))) or 0
    total_routes = await session.scalar(select(func.count(Route.id))) or 0

    return templates.TemplateResponse(request, "dashboard.html", {
        "total_users": total_users, "total_drivers": total_drivers,
        "today_orders": today_orders, "today_completed": today_departed,
        "today_revenue": today_revenue, "active_orders": active_trips,
        "total_orders": total_orders, "total_completed": total_departed,
        "total_revenue": total_revenue, "total_trips": total_trips,
        "active_trips": active_trips, "total_routes": total_routes,
    })
