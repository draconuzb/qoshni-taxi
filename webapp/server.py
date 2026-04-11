import logging
import math
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.database import async_session
from core.enums import DriverStatus, TripStatus, TripDirection, UserRole
from core.models import Driver, Route, Trip, Booking, UserRoute
from core.models.user import User
from core.locations import REGIONS, get_full_location

logger = logging.getLogger(__name__)

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN") or secrets.token_urlsafe(32)
_SESSION_COOKIE = "admin_session"
_session_tokens: set[str] = set()

if not os.environ.get("ADMIN_TOKEN"):
    logger.warning("ADMIN_TOKEN not set. Generated token: %s", ADMIN_TOKEN)


class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith("/static") or path == "/login":
            return await call_next(request)
        session_token = request.cookies.get(_SESSION_COOKIE)
        if not session_token or session_token not in _session_tokens:
            return RedirectResponse("/login", status_code=302)
        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(AuthMiddleware)
app.add_middleware(NoCacheMiddleware)
app.mount("/static", StaticFiles(directory="webapp/static"), name="static")
templates = Jinja2Templates(directory="webapp/templates")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    return HTMLResponse(
        f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Admin Login</title>
<style>
body{{font-family:sans-serif;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#f5f5f5}}
.card{{background:#fff;padding:2rem;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,.1);width:100%;max-width:400px}}
h2{{margin-top:0;text-align:center}}
input[type=password]{{width:100%;padding:.75rem;border:1px solid #ddd;border-radius:4px;box-sizing:border-box;margin:.5rem 0 1rem}}
button{{width:100%;padding:.75rem;background:#007bff;color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:1rem}}
button:hover{{background:#0056b3}}
.error{{color:red;text-align:center;margin-bottom:1rem}}
</style></head><body>
<div class="card"><h2>Admin Panel</h2>
{"<p class='error'>Invalid token</p>" if error else ""}
<form method="post" action="/login">
<label>Admin Token</label><input type="password" name="token" autofocus required>
<button type="submit">Login</button>
</form></div></body></html>"""
    )


@app.post("/login")
async def login_submit(request: Request):
    form = await request.form()
    token = form.get("token", "")
    if not secrets.compare_digest(str(token), ADMIN_TOKEN):
        return RedirectResponse("/login?error=1", status_code=302)
    session_token = secrets.token_urlsafe(32)
    _session_tokens.add(session_token)
    response = RedirectResponse("/", status_code=302)
    response.set_cookie(_SESSION_COOKIE, session_token, httponly=True, samesite="lax")
    return response


async def get_session():
    async with async_session() as session:
        yield session

PAGE_SIZE = 20


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session)):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total_users = await session.scalar(select(func.count(User.id))) or 0
    total_drivers = await session.scalar(select(func.count(Driver.id))) or 0
    online_drivers = await session.scalar(select(func.count(Driver.id)).where(Driver.is_online == True)) or 0
    pending_drivers = await session.scalar(select(func.count(Driver.id)).where(Driver.status == DriverStatus.PENDING_VERIFICATION)) or 0

    today_orders = await session.scalar(select(func.count(Booking.id)).where(Booking.created_at >= today_start)) or 0
    today_completed = await session.scalar(select(func.count(Trip.id)).where(and_(Trip.status == TripStatus.COMPLETED, Trip.completed_at >= today_start))) or 0
    today_revenue = await session.scalar(select(func.coalesce(func.sum(Trip.price_per_seat * Trip.booked_seats), 0)).where(and_(Trip.status == TripStatus.COMPLETED, Trip.completed_at >= today_start))) or 0
    active_orders = await session.scalar(select(func.count(Trip.id)).where(Trip.status.in_([TripStatus.COLLECTING, TripStatus.DEPARTED]))) or 0
    total_orders = await session.scalar(select(func.count(Booking.id))) or 0
    total_completed = await session.scalar(select(func.count(Trip.id)).where(Trip.status == TripStatus.COMPLETED)) or 0
    total_revenue = await session.scalar(select(func.coalesce(func.sum(Trip.price_per_seat * Trip.booked_seats), 0)).where(Trip.status == TripStatus.COMPLETED)) or 0
    total_trips = await session.scalar(select(func.count(Trip.id))) or 0
    active_trips = await session.scalar(select(func.count(Trip.id)).where(Trip.status.in_([TripStatus.COLLECTING, TripStatus.DEPARTED]))) or 0
    total_routes = await session.scalar(select(func.count(Route.id))) or 0

    return templates.TemplateResponse(request, "dashboard.html", {
        "total_users": total_users, "total_drivers": total_drivers,
        "online_drivers": online_drivers, "pending_drivers": pending_drivers,
        "today_orders": today_orders, "today_completed": today_completed,
        "today_revenue": today_revenue, "active_orders": active_orders,
        "total_orders": total_orders, "total_completed": total_completed,
        "total_revenue": total_revenue, "total_trips": total_trips,
        "active_trips": active_trips, "total_routes": total_routes,
    })


# ── Drivers ───────────────────────────────────────────────────────────────────

@app.get("/drivers", response_class=HTMLResponse)
async def drivers_page(request: Request, filter: str = "all", page: int = 1, session: AsyncSession = Depends(get_session)):
    query = select(Driver, User).join(User, Driver.user_id == User.id)
    if filter == "pending": query = query.where(Driver.status == DriverStatus.PENDING_VERIFICATION)
    elif filter == "verified": query = query.where(Driver.status == DriverStatus.VERIFIED)
    elif filter == "blocked": query = query.where(Driver.status == DriverStatus.BLOCKED)
    elif filter == "rejected": query = query.where(Driver.status == DriverStatus.REJECTED)
    elif filter == "online": query = query.where(and_(Driver.is_online == True, Driver.status == DriverStatus.VERIFIED))
    elif filter == "offline": query = query.where(and_(Driver.is_online == False, Driver.status == DriverStatus.VERIFIED))

    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    result = await session.execute(query.order_by(Driver.created_at.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))
    rows = result.all()
    pending_count = await session.scalar(select(func.count(Driver.id)).where(Driver.status == DriverStatus.PENDING_VERIFICATION)) or 0

    return templates.TemplateResponse(request, "drivers.html", {
        "drivers": rows, "filter": filter, "page": page, "total_pages": total_pages, "total": total, "pending_count": pending_count,
    })


@app.get("/drivers/{driver_id}", response_class=HTMLResponse)
async def driver_detail(request: Request, driver_id: int, session: AsyncSession = Depends(get_session)):
    driver = await session.get(Driver, driver_id)
    if not driver: raise HTTPException(404)
    user = await session.get(User, driver.user_id)

    routes = []
    if driver.route_id:
        route = await session.get(Route, driver.route_id)
        if route: routes.append(route)
    result = await session.execute(select(Route).where(Route.is_active == True).order_by(Route.id))
    all_routes = result.scalars().all()

    # Stats from trips
    orders_count = await session.scalar(select(func.count(Trip.id)).where(Trip.driver_id == driver_id)) or 0
    completed = await session.scalar(select(func.count(Trip.id)).where(and_(Trip.driver_id == driver_id, Trip.status == TripStatus.COMPLETED))) or 0
    revenue = await session.scalar(select(func.coalesce(func.sum(Trip.price_per_seat * Trip.booked_seats), 0)).where(and_(Trip.driver_id == driver_id, Trip.status == TripStatus.COMPLETED))) or 0

    result = await session.execute(
        select(Trip).where(Trip.driver_id == driver_id).options(selectinload(Trip.route)).order_by(Trip.created_at.desc()).limit(10)
    )
    recent_orders = result.scalars().all()

    return templates.TemplateResponse(request, "driver_detail.html", {
        "driver": driver, "user": user, "routes": routes, "all_routes": all_routes,
        "orders_count": orders_count, "completed": completed, "revenue": revenue, "recent_orders": recent_orders,
    })


# Driver API endpoints
@app.post("/api/drivers/{driver_id}/verify")
async def api_verify_driver(driver_id: int, session: AsyncSession = Depends(get_session)):
    driver = await session.get(Driver, driver_id)
    if not driver: raise HTTPException(404)
    driver.status = DriverStatus.VERIFIED
    await session.commit()
    return {"ok": True}

@app.post("/api/drivers/{driver_id}/reject")
async def api_reject_driver(driver_id: int, session: AsyncSession = Depends(get_session)):
    driver = await session.get(Driver, driver_id)
    if not driver: raise HTTPException(404)
    driver.status = DriverStatus.REJECTED
    await session.commit()
    return {"ok": True}

@app.post("/api/drivers/{driver_id}/block")
async def api_block_driver(driver_id: int, session: AsyncSession = Depends(get_session)):
    driver = await session.get(Driver, driver_id)
    if not driver: raise HTTPException(404)
    driver.status = DriverStatus.BLOCKED
    await session.commit()
    return {"ok": True}

@app.post("/api/drivers/{driver_id}/unblock")
async def api_unblock_driver(driver_id: int, session: AsyncSession = Depends(get_session)):
    driver = await session.get(Driver, driver_id)
    if not driver: raise HTTPException(404)
    driver.status = DriverStatus.VERIFIED
    await session.commit()
    return {"ok": True}

@app.delete("/api/drivers/{driver_id}")
async def api_delete_driver(driver_id: int, session: AsyncSession = Depends(get_session)):
    driver = await session.get(Driver, driver_id)
    if not driver: raise HTTPException(404)
    trips = (await session.execute(select(Trip).where(Trip.driver_id == driver.id))).scalars().all()
    for trip in trips:
        await session.execute(Booking.__table__.delete().where(Booking.trip_id == trip.id))
        await session.delete(trip)
    user = await session.get(User, driver.user_id)
    if user: user.role = UserRole.USER
    await session.delete(driver)
    await session.commit()
    return {"ok": True}

@app.post("/api/drivers/{driver_id}/assign-route")
async def api_assign_route(driver_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    data = await request.json()
    driver = await session.get(Driver, driver_id)
    if not driver: raise HTTPException(404)
    route_id = data.get("route_id")
    driver.route_id = int(route_id) if route_id else None
    await session.commit()
    return {"ok": True}

@app.post("/api/drivers/{driver_id}/update")
async def api_update_driver(driver_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    data = await request.json()
    driver = await session.get(Driver, driver_id)
    if not driver: raise HTTPException(404)
    if "car_model" in data: driver.car_model = data["car_model"]
    if "car_color" in data: driver.car_color = data["car_color"]
    if "license_plate" in data: driver.license_plate = data["license_plate"]
    await session.commit()
    return {"ok": True}


# ── Trips ─────────────────────────────────────────────────────────────────────

@app.get("/trips", response_class=HTMLResponse)
async def trips_page(request: Request, filter: str = "all", page: int = 1, session: AsyncSession = Depends(get_session)):
    query = select(Trip).options(selectinload(Trip.route), selectinload(Trip.driver).selectinload(Driver.user))
    status_map = {"collecting": TripStatus.COLLECTING, "departed": TripStatus.DEPARTED, "completed": TripStatus.COMPLETED, "cancelled": TripStatus.CANCELLED}
    if filter in status_map: query = query.where(Trip.status == status_map[filter])

    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    result = await session.execute(query.order_by(Trip.created_at.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))
    trips = result.scalars().all()

    return templates.TemplateResponse(request, "trips.html", {
        "trips": trips, "filter": filter, "page": page, "total_pages": total_pages, "total": total, "TripDirection": TripDirection,
    })

@app.get("/trips/{trip_id}", response_class=HTMLResponse)
async def trip_detail(request: Request, trip_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Trip).where(Trip.id == trip_id).options(
            selectinload(Trip.route), selectinload(Trip.driver).selectinload(Driver.user),
            selectinload(Trip.bookings).selectinload(Booking.user),
        )
    )
    trip = result.scalar_one_or_none()
    if not trip: raise HTTPException(404)
    return templates.TemplateResponse(request, "trip_detail.html", {"trip": trip, "TripDirection": TripDirection})

@app.post("/api/trips/{trip_id}/cancel")
async def api_cancel_trip(trip_id: int, session: AsyncSession = Depends(get_session)):
    trip = await session.get(Trip, trip_id)
    if not trip: raise HTTPException(404)
    if trip.status not in (TripStatus.COLLECTING, TripStatus.DEPARTED):
        raise HTTPException(400, detail="Only collecting or departed trips can be cancelled")
    trip.status = TripStatus.CANCELLED
    await session.commit()
    return {"ok": True}

@app.post("/api/trips/{trip_id}/complete")
async def api_complete_trip(trip_id: int, session: AsyncSession = Depends(get_session)):
    trip = await session.get(Trip, trip_id)
    if not trip: raise HTTPException(404)
    if trip.status != TripStatus.DEPARTED:
        raise HTTPException(400, detail="Only departed trips can be completed")
    trip.status = TripStatus.COMPLETED
    trip.completed_at = datetime.utcnow()
    await session.commit()
    return {"ok": True}


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/routes", response_class=HTMLResponse)
async def routes_page(request: Request, page: int = 1, session: AsyncSession = Depends(get_session)):
    total = await session.scalar(select(func.count(Route.id))) or 0
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    result = await session.execute(select(Route).order_by(Route.id).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))
    routes = result.scalars().all()

    route_stats = {}
    for route in routes:
        trips_count = await session.scalar(select(func.count(Trip.id)).where(Trip.route_id == route.id)) or 0
        completed = await session.scalar(select(func.count(Trip.id)).where(and_(Trip.route_id == route.id, Trip.status == TripStatus.COMPLETED))) or 0
        revenue = await session.scalar(select(func.coalesce(func.sum(Trip.price_per_seat * Trip.booked_seats), 0)).where(and_(Trip.route_id == route.id, Trip.status == TripStatus.COMPLETED))) or 0
        driver_count = await session.scalar(select(func.count(Driver.id)).where(Driver.route_id == route.id)) or 0
        route_stats[route.id] = {"orders": trips_count, "completed": completed, "revenue": revenue, "drivers": driver_count}

    return templates.TemplateResponse(request, "routes.html", {
        "routes": routes, "route_stats": route_stats, "page": page, "total_pages": total_pages, "total": total,
    })

@app.get("/api/locations/regions")
async def api_regions():
    return [{"id": k, "name": v["name"]} for k, v in REGIONS.items()]

@app.get("/api/locations/districts/{region_id}")
async def api_districts(region_id: str):
    region = REGIONS.get(region_id)
    if not region: raise HTTPException(404)
    return [{"id": k, "name": v} for k, v in region["districts"].items()]

@app.post("/api/routes", response_class=JSONResponse)
async def api_create_route(request: Request, session: AsyncSession = Depends(get_session)):
    data = await request.json()
    route = Route(name=data.get("name", ""), region=data["region"], district=data["district"],
                  from_name=data["from_name"], to_name=data["to_name"], price=int(data["price"]))
    session.add(route)
    await session.commit()
    return {"ok": True, "id": route.id}

@app.post("/api/routes/{route_id}/toggle")
async def api_toggle_route(route_id: int, session: AsyncSession = Depends(get_session)):
    route = await session.get(Route, route_id)
    if not route: raise HTTPException(404)
    route.is_active = not route.is_active
    await session.commit()
    return {"ok": True, "is_active": route.is_active}

@app.post("/api/routes/{route_id}/price")
async def api_update_price(route_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    data = await request.json()
    route = await session.get(Route, route_id)
    if not route: raise HTTPException(404)
    route.price = int(data["price"])
    await session.commit()
    return {"ok": True}

@app.delete("/api/routes/{route_id}")
async def api_delete_route(route_id: int, session: AsyncSession = Depends(get_session)):
    route = await session.get(Route, route_id)
    if not route: raise HTTPException(404)
    await session.delete(route)
    await session.commit()
    return {"ok": True}


# ── Users ─────────────────────────────────────────────────────────────────────

@app.get("/users", response_class=HTMLResponse)
async def users_page(request: Request, q: str = "", role: str = "all", page: int = 1, session: AsyncSession = Depends(get_session)):
    query = select(User)
    if q: query = query.where(User.full_name.ilike(f"%{q}%") | User.phone.ilike(f"%{q}%"))
    if role != "all": query = query.where(User.role == role)

    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    result = await session.execute(query.order_by(User.created_at.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))
    users = result.scalars().all()

    return templates.TemplateResponse(request, "users.html", {
        "users": users, "q": q, "role": role, "page": page, "total_pages": total_pages, "total": total,
    })

@app.get("/users/{user_id}", response_class=HTMLResponse)
async def user_detail(request: Request, user_id: int, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if not user: raise HTTPException(404)

    # Booking stats
    total_bookings = await session.scalar(select(func.count(Booking.id)).where(Booking.user_id == user_id)) or 0

    # Recent bookings
    result = await session.execute(
        select(Booking).where(Booking.user_id == user_id)
        .options(selectinload(Booking.trip).selectinload(Trip.route))
        .order_by(Booking.created_at.desc()).limit(10)
    )
    recent_bookings = result.scalars().all()

    # Favorite routes
    result = await session.execute(
        select(UserRoute).where(UserRoute.user_id == user_id).options(selectinload(UserRoute.route))
    )
    fav_routes = result.scalars().all()

    return templates.TemplateResponse(request, "user_detail.html", {
        "user": user, "total_bookings": total_bookings, "recent_bookings": recent_bookings, "fav_routes": fav_routes,
    })

@app.post("/api/users/{user_id}/block")
async def api_block_user(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if not user: raise HTTPException(404)
    user.is_blocked = True
    await session.commit()
    return {"ok": True}

@app.post("/api/users/{user_id}/unblock")
async def api_unblock_user(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if not user: raise HTTPException(404)
    user.is_blocked = False
    await session.commit()
    return {"ok": True}

@app.delete("/api/users/{user_id}")
async def api_delete_user(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if not user: raise HTTPException(404)
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

@app.post("/api/users/{user_id}/role")
async def api_change_role(user_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    data = await request.json()
    user = await session.get(User, user_id)
    if not user: raise HTTPException(404)
    new_role = data.get("role")
    if new_role not in [r.value for r in UserRole]: raise HTTPException(400)
    user.role = UserRole(new_role)
    await session.commit()
    return {"ok": True}

@app.post("/api/users/{user_id}/update")
async def api_update_user(user_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    data = await request.json()
    user = await session.get(User, user_id)
    if not user: raise HTTPException(404)
    if "full_name" in data: user.full_name = data["full_name"]
    if "phone" in data: user.phone = data["phone"]
    await session.commit()
    return {"ok": True}


# ── Settings ──────────────────────────────────────────────────────────────────

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, session: AsyncSession = Depends(get_session)):
    from infrastructure.config import settings as app_settings
    total_routes = await session.scalar(select(func.count(Route.id))) or 0
    active_routes = await session.scalar(select(func.count(Route.id)).where(Route.is_active == True)) or 0
    return templates.TemplateResponse(request, "settings.html", {
        "settings": app_settings, "total_routes": total_routes, "active_routes": active_routes, "regions": REGIONS,
    })
