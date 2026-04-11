from aiogram import Router

from bot.handlers.driver.trip import router as trip_router

router = Router(name="driver")
router.include_routers(trip_router)
