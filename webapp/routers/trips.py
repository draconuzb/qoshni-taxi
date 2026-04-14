import math

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.enums import TripStatus, TripDirection
from core.models import Driver, Trip, Booking
from webapp.deps import get_session, templates, PAGE_SIZE

router = APIRouter()


@router.get("/trips", response_class=HTMLResponse)
async def trips_page(request: Request, filter: str = "all", page: int = 1, session: AsyncSession = Depends(get_session)):
    query = select(Trip).options(
        selectinload(Trip.route),
        selectinload(Trip.driver).selectinload(Driver.user),
    )
    status_map = {
        "collecting": TripStatus.COLLECTING,
        "departed": TripStatus.DEPARTED,
        "cancelled": TripStatus.CANCELLED,
    }
    if filter in status_map:
        query = query.where(Trip.status == status_map[filter])

    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    result = await session.execute(
        query.order_by(Trip.created_at.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    )
    trips = result.scalars().all()

    return templates.TemplateResponse(request, "trips.html", {
        "trips": trips, "filter": filter, "page": page, "total_pages": total_pages,
        "total": total, "TripDirection": TripDirection,
    })


@router.get("/trips/{trip_id}", response_class=HTMLResponse)
async def trip_detail(request: Request, trip_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Trip).where(Trip.id == trip_id).options(
            selectinload(Trip.route),
            selectinload(Trip.driver).selectinload(Driver.user),
            selectinload(Trip.bookings).selectinload(Booking.user),
        )
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(404)
    return templates.TemplateResponse(request, "trip_detail.html", {"trip": trip, "TripDirection": TripDirection})


@router.post("/api/trips/{trip_id}/cancel")
async def api_cancel_trip(trip_id: int, session: AsyncSession = Depends(get_session)):
    trip = await session.get(Trip, trip_id)
    if not trip:
        raise HTTPException(404)
    if trip.status not in (TripStatus.COLLECTING, TripStatus.DEPARTED):
        raise HTTPException(400, detail="Only collecting or departed trips can be cancelled")
    trip.status = TripStatus.CANCELLED
    await session.commit()
    return {"ok": True}
