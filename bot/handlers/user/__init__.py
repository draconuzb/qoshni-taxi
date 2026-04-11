from aiogram import Router

from bot.handlers.user.start import router as start_router
from bot.handlers.user.order import router as order_router

router = Router(name="user")
router.include_routers(start_router, order_router)
