import math

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.enums import UserRole
from core.models import Driver, Trip, Booking, UserRoute
from core.models.user import User
from webapp.deps import get_session, templates, PAGE_SIZE

router = APIRouter()


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)


class UserRoleChange(BaseModel):
    role: str


@router.get("/users", response_class=HTMLResponse)
async def users_page(
    request: Request,
    q: str = "",
    role: str = "all",
    page: int = 1,
    session: AsyncSession = Depends(get_session),
):
    query = select(User)
    if q:
        like = f"%{q}%"
        query = query.where(or_(User.full_name.ilike(like), User.phone.ilike(like)))
    if role != "all":
        query = query.where(User.role == role)

    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    result = await session.execute(
        query.order_by(User.created_at.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    )
    users = result.scalars().all()

    return templates.TemplateResponse(request, "users.html", {
        "users": users, "q": q, "role": role, "page": page,
        "total_pages": total_pages, "total": total,
    })


@router.get("/users/{user_id}", response_class=HTMLResponse)
async def user_detail(request: Request, user_id: int, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(404)

    total_bookings = await session.scalar(
        select(func.count(Booking.id)).where(Booking.user_id == user_id)
    ) or 0

    result = await session.execute(
        select(Booking).where(Booking.user_id == user_id)
        .options(selectinload(Booking.trip).selectinload(Trip.route))
        .order_by(Booking.created_at.desc()).limit(10)
    )
    recent_bookings = result.scalars().all()

    result = await session.execute(
        select(UserRoute).where(UserRoute.user_id == user_id).options(selectinload(UserRoute.route))
    )
    fav_routes = result.scalars().all()

    return templates.TemplateResponse(request, "user_detail.html", {
        "user": user, "total_bookings": total_bookings,
        "recent_bookings": recent_bookings, "fav_routes": fav_routes,
    })


@router.post("/api/users/{user_id}/block")
async def api_block_user(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(404)
    user.is_blocked = True
    await session.commit()
    return {"ok": True}


@router.post("/api/users/{user_id}/unblock")
async def api_unblock_user(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(404)
    user.is_blocked = False
    await session.commit()
    return {"ok": True}


@router.delete("/api/users/{user_id}")
async def api_delete_user(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(404)
    driver = (await session.execute(select(Driver).where(Driver.user_id == user_id))).scalar_one_or_none()
    if driver:
        trips = (await session.execute(select(Trip).where(Trip.driver_id == driver.id))).scalars().all()
        for trip in trips:
            await session.execute(Booking.__table__.delete().where(Booking.trip_id == trip.id))
            await session.delete(trip)
        await session.delete(driver)
    await session.execute(Booking.__table__.delete().where(Booking.user_id == user_id))
    await session.execute(UserRoute.__table__.delete().where(UserRoute.user_id == user_id))
    await session.delete(user)
    await session.commit()
    return {"ok": True}


@router.post("/api/users/{user_id}/role")
async def api_change_role(user_id: int, data: UserRoleChange, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(404)
    if data.role not in [r.value for r in UserRole]:
        raise HTTPException(400, detail="Invalid role")
    user.role = UserRole(data.role)
    await session.commit()
    return {"ok": True}


@router.post("/api/users/{user_id}/update")
async def api_update_user(user_id: int, data: UserUpdate, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(404)
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.phone is not None:
        user.phone = data.phone
    await session.commit()
    return {"ok": True}
