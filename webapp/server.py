import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware

from infrastructure.config import settings as app_settings
from infrastructure.database import async_session
from infrastructure import session_store
from webapp.deps import templates
from webapp.routers import (
    dashboard_router, drivers_router, trips_router,
    routes_router, users_router, settings_router,
)

logger = logging.getLogger(__name__)

ADMIN_PHONE = app_settings.admin_phone
ADMIN_PASSWORD = app_settings.admin_password
SESSION_TTL = app_settings.session_ttl_seconds
SESSION_SECURE = app_settings.session_secure_cookie

_SESSION_COOKIE = "admin_session"
_CSRF_COOKIE = "csrf_token"
_CSRF_HEADER = "x-csrf-token"
_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_PUBLIC_PATHS = {"/login", "/logout", "/health", "/favicon.ico"}

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
            if (not cookie_token or not header_token
                    or not secrets.compare_digest(cookie_token, header_token)):
                return JSONResponse({"error": "csrf_failed"}, status_code=403)
        response = await call_next(request)
        if not request.cookies.get(_CSRF_COOKIE):
            response.set_cookie(
                _CSRF_COOKIE, secrets.token_urlsafe(32),
                httponly=False, samesite="lax", secure=SESSION_SECURE,
                max_age=SESSION_TTL,
            )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not ADMIN_PHONE or not ADMIN_PASSWORD:
        logger.error("ADMIN_PHONE / ADMIN_PASSWORD not configured — login is DISABLED")
    yield
    await session_store.close()


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CSRFMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(NoCacheMiddleware)
app.mount("/static", StaticFiles(directory="webapp/static"), name="static")


@app.get("/health")
async def health():
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
    return templates.TemplateResponse(request, "login.html", {
        "error": bool(error),
        "error_message": (
            "Juda ko'p urinish. Keyinroq urinib ko'ring." if error == "rate"
            else "Telefon yoki parol noto'g'ri"
        ),
    })


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
        logger.info("Failed login: ip=%s phone=%s", ip, (phone[:6] + "***") if phone else "-")
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
    return response


@app.post("/logout")
async def logout(request: Request):
    token = request.cookies.get(_SESSION_COOKIE)
    if token:
        await session_store.session_delete(token)
    response = RedirectResponse("/login", status_code=302)
    response.delete_cookie(_SESSION_COOKIE)
    return response


app.include_router(dashboard_router)
app.include_router(drivers_router)
app.include_router(trips_router)
app.include_router(routes_router)
app.include_router(users_router)
app.include_router(settings_router)
