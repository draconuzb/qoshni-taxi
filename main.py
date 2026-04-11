import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers.user import router as user_router
from bot.handlers.driver import router as driver_router
from bot.handlers.admin import router as admin_router
from bot.middlewares.db import DbSessionMiddleware
from bot.middlewares.auth import AuthMiddleware
from infrastructure.config import settings
from infrastructure.database import engine, Base

import core.models  # noqa: F401


async def run_webapp():
    import uvicorn
    from webapp.server import app
    config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logging.info("Database jadvallari tayyor!")

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(AuthMiddleware())

    dp.include_routers(admin_router, driver_router, user_router)

    asyncio.create_task(run_webapp())

    logging.info("TaxiBek bot ishga tushdi!")
    logging.info("Manager webapp: http://localhost:8080")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
