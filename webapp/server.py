import logging
import math
import secrets
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import select, func, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.database import async_session
from infrastructure.config import settings as app_settings
from infrastructure import session_store
from core.enums import DriverStatus, TripStatus, TripDirection, UserRole
from core.models import Driver, Route, Trip, Booking, UserRoute
from core.models.user import User
from core.locations import REGIONS, get_full_location

logger = logging.getLogger(__name__)

ADMIN_PHONE = app_settings.admin_phone
ADMIN_PASSWORD = app_settings.admin_password
SESSION_TTL = app_settings.session_ttl_seconds
SESSION_SECURE = app_settings.session_secure_cookie

_SESSION_COOKIE = "admin_session"
_CSRF_COOKIE = "csrf_token"
_CSRF_HEADER = "x-csrf-token"
_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_PUBLIC_PATHS = {"/login", "/health", "/favicon.ico"}

LOGIN_RATE_LIMIT_ATTEMPTS = 5
LOGIN_RATE_LIMIT_WINDOW = 300


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
        if path.startswith("/static") or path in _PUBLIC_PATHS:
            return await call_next(request)
        token = request.cookies.get(_SESSION_COOKIE)
        if not await session_store.session_is_valid(token):
            if path.startswith("/api/"):
                return JSONResponse({"error": "unauthorized"}, status_code=401)
            return RedirectResponse("/login", status_code=302)
        return await call_next(request)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Double-submit cookie CSRF protection for unsafe methods on /api/*."""

    async def dispatch(self, request: Request, call_next):
        if request.method in _UNSAFE_METHODS and request.url.path.startswith("/api/"):
            cookie_token = request.cookies.get(_CSRF_COOKIE)
            header_token = request.headers.get(_CSRF_HEADER)
            if not cookie_token or not header_token or not secrets.compare_digest(cookie_token, header_token):
                return JSONResponse({"error": "csrf_failed"}, status_code=403)
        response = await call_next(request)
        if not request.cookies.get(_CSRF_COOKIE):
            response.set_cookie(
                _CSRF_COOKIE,
                secrets.token_urlsafe(32),
                httponly=False,
                samesite="lax",
                secure=SESSION_SECURE,
                max_age=SESSION_TTL,
            )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not ADMIN_PHONE or not ADMIN_PASSWORD:
        logger.error("ADMIN_PHONE / ADMIN_PASSWORD not configured — login is DISABLED")
    yield
    await session_store.close()


app = FastAPI(lifespan=lifespan)
app.add_middleware(CSRFMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(NoCacheMiddleware)
app.mount("/static", StaticFiles(directory="webapp/static"), name="static")
templates = Jinja2Templates(directory="webapp/templates")


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.get("/health")
async def health():
    """Liveness + DB probe."""
    db_ok = True
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
    except Exception as e:
        logger.error("Health DB check failed: %s", e)
        db_ok = False
    return JSONResponse(
        {"ok": db_ok, "status": "healthy" if db_ok else "degraded"},
        status_code=200 if db_ok else 503,
    )


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    return templates.TemplateResponse(
        request,
        "login.html",
        {
            "error": bool(error),
            "error_message": "Juda ko'p urinish. Keyinroq urinib ko'ring." if error == "rate"
                             else "Telefon yoki parol noto'g'ri",
        },
    )


@app.post("/login")
async def login_submit(request: Request):
    ip = _client_ip(request)
    allowed, retry = await session_store.rate_limit_check(
        f"login:{ip}", LOGIN_RATE_LIMIT_ATTEMPTS, LOGIN_RATE_LIMIT_WINDOW,
    )
    if not allowed:
        logger.warning("Login rate-limited: ip=%s retry=%ds", ip, retry)
        return RedirectResponse("/login?error=rate", status_code=302)

    form = await request.form()
    phone = str(form.get("phone", "")).strip()
    password = str(form.get("password", "")).strip()

    if not ADMIN_PHONE or not ADMIN_PASSWORD:
        logger.error("Login attempt while admin creds unset")
        return RedirectResponse("/login?error=1", status_code=302)

    phone_ok = secrets.compare_digest(phone, ADMIN_PHONE)
    pwd_ok = secrets.compare_digest(password, ADMIN_PASSWORD)
    if not (phone_ok and pwd_ok):
        logger.info("Failed login: ip=%s phone=%s", ip, phone[:6] + "***")
        return RedirectResponse("/login?error=1", status_code=302)

    session_token = secrets.token_urlsafe(32)
    await session_store.session_create(session_token, SESSION_TTL)
    logger.info("Login success: ip=%s", ip)

    response = RedirectResponse("/", status_code=302)
    response.set_cookie(
        _SESSION_COOKIE, session_token,
        httponly=True, samesite="lax", secure=SESSION_SECURE,
        max_age=SESSION_TTL,
    )
    response.set_cookie(
        _CSRF_COOKIE, secrets.token_urlsafe(32),
        httponly=False, samesite="lax", secure=SESSION_SECURE,
        max_age=SESSION_TTL,
    )
    return response


@app.post("/logout")
async def logout(request: Request):
    token = request.cookies.get(_SESSION_COOKIE)
    if token:
        await session_store.session_delete(token)
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(_SESSION_COOKIE)
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
    today_orders = await session.scalar(select(func.count(Booking.id)).where(Booking.created_at >= today_start)) or 0
    today_departed = await session.scalar(select(func.count(Trip.id)).where(and_(Trip.status == TripStatus.DEPARTED, Trip.departed_at >= today_start))) or 0
    today_revenue = await session.scalar(select(func.coalesce(func.sum(Trip.price_per_seat * Trip.booked_seats), 0)).where(and_(Trip.status == TripStatus.DEPARTED, Trip.departed_at >= today_start))) or 0
    active_trips = await session.scalar(select(func.count(Trip.id)).where(Trip.status == TripStatus.COLLECTING)) or 0
    total_orders = await session.scalar(select(func.count(Booking.id))) or 0
    total_departed = await session.scalar(select(func.count(Trip.id)).where(Trip.status == TripStatus.DEPARTED)) or 0
    total_revenue = await session.scalar(select(func.coalesce(func.sum(Trip.price_per_seat * Trip.booked_seats), 0)).where(Trip.status == TripStatus.DEPARTED)) or 0
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


# ── Drivers ───────────────────────────────────────────────────────────────────

@app.get("/drivers", response_class=HTMLResponse)
async def drivers_page(request: Request, filter: str = "all", page: int = 1, session: AsyncSession = Depends(get_session)):
    query = select(Driver, User).join(User, Driver.user_id == User.id)
    if filter == "verified": query = query.where(Driver.status == DriverStatus.VERIFIED)
    elif filter == "blocked": query = query.where(Driver.status == DriverStatus.BLOCKED)

    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(1, min(page, total_pages))
    result = await session.execute(query.order_by(Driver.created_at.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))
    rows = result.all()
    pending_count = 0

    return templates.TemplateResponse(request, "drivers.html", {
        "drivers": rows, "filter": filter, "page": page, "total_pages": total_pages, "total": total, "pending_count": pending_count,
    })


@app.get("/drivers/{driver_id}", response_class=HTMLResponse)
async def driver_detail(request: Request, driver_id: int, session: AsyncSession = Depends(get_session)):
    driver = await session.get(Driver, driver_id)
    if not driver: raise HTTPException(404)
    user = await session.get(User, driver.user_id)

    # Stats from trips
    orders_count = await session.scalar(select(func.count(Trip.id)).where(Trip.driver_id == driver_id)) or 0
    completed = await session.scalar(select(func.count(Trip.id)).where(and_(Trip.driver_id == driver_id, Trip.status == TripStatus.DEPARTED))) or 0
    revenue = await session.scalar(select(func.coalesce(func.sum(Trip.price_per_seat * Trip.booked_seats), 0)).where(and_(Trip.driver_id == driver_id, Trip.status == TripStatus.DEPARTED))) or 0

    # Favorite routes
    fav_result = await session.execute(
        select(UserRoute).where(UserRoute.user_id == driver.user_id).options(selectinload(UserRoute.route))
    )
    routes = [fr.route for fr in fav_result.scalars().all()]
    all_routes = (await session.execute(select(Route).where(Route.is_active == True).order_by(Route.id))).scalars().all()

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
    driver.status = DriverStatus.BLOCKED
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
    status_map = {"collecting": TripStatus.COLLECTING, "departed": TripStatus.DEPARTED, "cancelled": TripStatus.CANCELLED}
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
        completed = await session.scalar(select(func.count(Trip.id)).where(and_(Trip.route_id == route.id, Trip.status == TripStatus.DEPARTED))) or 0
        revenue = await session.scalar(select(func.coalesce(func.sum(Trip.price_per_seat * Trip.booked_seats), 0)).where(and_(Trip.route_id == route.id, Trip.status == TripStatus.DEPARTED))) or 0
        driver_count = await session.scalar(select(func.count(UserRoute.id)).where(UserRoute.route_id == route.id)) or 0
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
    try:
        price = int(data.get("price", 0))
        if price < 0 or price > 100_000_000:
            raise ValueError("price out of range")
        route = Route(
            name=str(data.get("name", ""))[:100],
            region=str(data.get("region", ""))[:50],
            district=str(data.get("district", ""))[:50],
            from_name=str(data.get("from_name", ""))[:255],
            to_name=str(data.get("to_name", ""))[:255],
            price=price,
        )
    except (ValueError, TypeError, KeyError) as e:
        raise HTTPException(400, detail=f"Invalid input: {e}")
    if not route.from_name or not route.to_name:
        raise HTTPException(400, detail="from_name/to_name required")
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
    try:
        price = int(data.get("price", 0))
    except (ValueError, TypeError):
        raise HTTPException(400, detail="Invalid price")
    if price < 0 or price > 100_000_000:
        raise HTTPException(400, detail="Price out of range")
    route.price = price
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
    result = await session.execute(select(Route).where(Route.is_active == True).order_by(Route.id))
    all_routes = result.scalars().all()
    return templates.TemplateResponse(request, "settings.html", {
        "settings": app_settings, "total_routes": total_routes, "active_routes": active_routes,
        "regions": REGIONS, "all_routes": all_routes,
        "default_route_id": app_settings.default_route_id,
        "contact_phone": app_settings.contact_phone,
    })


@app.post("/api/settings/default-route")
async def api_set_default_route(request: Request):
    from infrastructure.config import settings as app_settings
    data = await request.json()
    route_id = int(data.get("route_id", 1))
    app_settings.default_route_id = route_id
    return {"ok": True}


@app.post("/api/settings/contact-phone")
async def api_set_contact_phone(request: Request):
    from infrastructure.config import settings as app_settings
    data = await request.json()
    phone = data.get("phone", "").strip()
    if phone:
        app_settings.contact_phone = phone
    return {"ok": True}
