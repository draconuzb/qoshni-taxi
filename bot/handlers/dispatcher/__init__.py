from aiogram import Router

from bot.handlers.dispatcher.panel import router as panel_router

router = Router(name="dispatcher")
router.include_routers(panel_router)
