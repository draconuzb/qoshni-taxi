from webapp.routers.dashboard import router as dashboard_router
from webapp.routers.drivers import router as drivers_router
from webapp.routers.trips import router as trips_router
from webapp.routers.routes import router as routes_router
from webapp.routers.users import router as users_router
from webapp.routers.settings import router as settings_router

__all__ = [
    "dashboard_router",
    "drivers_router",
    "trips_router",
    "routes_router",
    "users_router",
    "settings_router",
]
