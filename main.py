import asyncio
import logging
import signal
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers.user import router as user_router
from bot.handlers.driver import router as driver_router
from bot.handlers.admin import router as admin_router
from bot.middlewares.db import DbSessionMiddleware
from bot.middlewares.auth import AuthMiddleware
from bot.middlewares.ratelimit import RateLimitMiddleware
from infrastructure.config import settings
from infrastructure.database import engine, Base

import core.models  # noqa: F401


async def _run_migrations() -> None:
    """Apply Alembic migrations if versions/ has any; else create_all()."""
    versions_dir = Path(__file__).parent / "alembic" / "versions"
    has_migrations = versions_dir.is_dir() and any(
        p.suffix == ".py" and not p.name.startswith("__") for p in versions_dir.iterdir()
    )
    if has_migrations:
        try:
            from alembic import command
            from alembic.config import Config
            cfg = Config(str(Path(__file__).parent / "alembic.ini"))
            cfg.set_main_option("sqlalchemy.url", settings.database_url)
            cfg.set_main_option("script_location", str(Path(__file__).parent / "alembic"))
            await asyncio.to_thread(command.upgrade, cfg, "head")
            logging.info("Alembic: upgrade head complete")
            return
        except Exception as e:
            logging.error("Alembic upgrade failed, falling back to create_all: %s", e)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logging.info("Database jadvallari tayyor (create_all)!")


async def run_webapp(stop_event: asyncio.Event):
    import uvicorn
    from webapp.server import app
    config = uvicorn.Config(app, host="0.0.0.0", port=8080, log_level="info", access_log=False)
    server = uvicorn.Server(config)
    server_task = asyncio.create_task(server.serve())
    await stop_event.wait()
    server.should_exit = True
    await server_task


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

    await _run_migrations()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(RateLimitMiddleware(max_events=20, window_seconds=60.0))
    dp.update.middleware(AuthMiddleware())
    dp.include_routers(admin_router, driver_router, user_router)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _signal_handler():
        logging.info("Shutdown signal received — stopping gracefully…")
        stop_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except NotImplementedError:
            pass

    webapp_task = asyncio.create_task(run_webapp(stop_event))

    logging.info("TaxiBek bot ishga tushdi!")
    logging.info("Manager webapp: http://0.0.0.0:8080")

    polling_task = asyncio.create_task(dp.start_polling(bot))

    await stop_event.wait()

    logging.info("Stopping bot polling…")
    await dp.stop_polling()
    try:
        await asyncio.wait_for(polling_task, timeout=10)
    except (asyncio.TimeoutError, asyncio.CancelledError):
        polling_task.cancel()

    logging.info("Stopping webapp…")
    try:
        await asyncio.wait_for(webapp_task, timeout=10)
    except asyncio.TimeoutError:
        webapp_task.cancel()

    await bot.session.close()
    await engine.dispose()
    logging.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
