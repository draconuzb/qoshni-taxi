from aiogram import Router

from bot.handlers.manager.panel import router as panel_router
from bot.handlers.manager.routes import router as routes_router
from bot.handlers.manager.drivers import router as drivers_router
from bot.handlers.manager.trips import router as trips_router
from bot.handlers.manager.users import router as users_router
from bot.handlers.manager.orders import router as orders_router

router = Router(name="manager")
router.include_routers(panel_router, routes_router, drivers_router, trips_router, users_router, orders_router)
