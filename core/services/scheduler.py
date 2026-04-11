"""
Background scheduler — har 30 sekundda ishlaydi:
1. Pending buyurtmalarni tekshiradi (5 daqiqa o'tgan bo'lsa — qayta yuborish yoki expire)
2. Scheduled buyurtmalarni tekshiradi (vaqti kelgan bo'lsa — PENDING ga o'tkazish)
3. Haydovchi yetib kelganda yo'lovchiga vaqt xabari yuborish
"""

import asyncio
import logging
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2

from aiogram import Bot
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import (
    driver_order_action_kb,
    main_menu_kb,
)
from core.enums import OrderStatus, DriverStatus
from core.models import Order, Driver, Route
from core.models.driver import driver_routes
from core.models.user import User
from infrastructure.database import async_session

logger = logging.getLogger(__name__)

ORDER_TIMEOUT_MINUTES = 5
MAX_RETRIES = 2
SCHEDULER_INTERVAL = 30  # sekundda


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Ikki nuqta orasidagi masofani km da hisoblash."""
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def estimate_minutes(distance_km: float, speed_kmh: float = 40) -> int:
    """Taxminiy yetib kelish vaqti (daqiqada)."""
    if distance_km <= 0:
        return 1
    return max(1, round(distance_km / speed_kmh * 60))


async def check_expired_orders(bot: Bot):
    """5 daqiqada qabul qilinmagan buyurtmalarni qayta yuborish yoki expire qilish."""
    async with async_session() as session:
        cutoff = datetime.utcnow() - timedelta(minutes=ORDER_TIMEOUT_MINUTES)

        result = await session.execute(
            select(Order).where(
                and_(
                    Order.status == OrderStatus.PENDING,
                    Order.is_scheduled == False,
                    Order.created_at < cutoff,
                )
            )
        )
        orders = result.scalars().all()

        for order in orders:
            if order.retry_count < MAX_RETRIES:
                # Qayta yuborish
                order.retry_count += 1
                order.notified_at = datetime.utcnow()
                await session.commit()

                await _resend_to_drivers(bot, session, order)

                # Yo'lovchiga xabar
                user = await session.get(User, order.user_id)
                if user:
                    try:
                        await bot.send_message(
                            user.telegram_id,
                            f"🔄 <b>Buyurtma #{order.id}</b> — haydovchi hali topilmadi.\n"
                            f"Qayta qidirilmoqda... (urinish {order.retry_count}/{MAX_RETRIES})",
                        )
                    except Exception:
                        pass

                logger.info(f"Order #{order.id} — qayta yuborildi (urinish {order.retry_count})")
            else:
                # Expire qilish
                order.status = OrderStatus.EXPIRED
                await session.commit()

                user = await session.get(User, order.user_id)
                if user:
                    try:
                        await bot.send_message(
                            user.telegram_id,
                            f"⏰ <b>Buyurtma #{order.id} muddati tugadi.</b>\n\n"
                            "Afsuski, haydovchi topilmadi.\n"
                            "Qayta buyurtma berishingiz mumkin.",
                            reply_markup=main_menu_kb(),
                        )
                    except Exception:
                        pass

                logger.info(f"Order #{order.id} — expired (haydovchi topilmadi)")


async def check_scheduled_orders(bot: Bot):
    """Vaqti kelgan scheduled buyurtmalarni faollashtirish."""
    async with async_session() as session:
        now = datetime.utcnow()
        # 15 daqiqa oldin haydovchilarga xabar yuborish
        notify_window = now + timedelta(minutes=15)

        result = await session.execute(
            select(Order).where(
                and_(
                    Order.status == OrderStatus.SCHEDULED,
                    Order.is_scheduled == True,
                    Order.scheduled_at <= notify_window,
                )
            )
        )
        orders = result.scalars().all()

        for order in orders:
            if order.scheduled_at <= now:
                # Vaqti keldi — PENDING ga o'tkazish
                order.status = OrderStatus.PENDING
                order.notified_at = datetime.utcnow()
                await session.commit()

                await _resend_to_drivers(bot, session, order)

                user = await session.get(User, order.user_id)
                if user:
                    route = await session.get(Route, order.route_id)
                    route_text = f"{route.from_name} → {route.to_name}" if route else "—"
                    try:
                        await bot.send_message(
                            user.telegram_id,
                            f"🕐 <b>Rejalashtirilgan buyurtma #{order.id} faollashdi!</b>\n\n"
                            f"🛣 {route_text}\n"
                            "Haydovchi qidirilmoqda...",
                        )
                    except Exception:
                        pass

                logger.info(f"Scheduled order #{order.id} activated")

            elif order.notified_at is None:
                # 15 daqiqa qoldi — haydovchilarga oldindan xabar
                order.notified_at = datetime.utcnow()
                await session.commit()

                await _notify_drivers_upcoming(bot, session, order)
                logger.info(f"Scheduled order #{order.id} — drivers pre-notified")


async def _resend_to_drivers(bot: Bot, session: AsyncSession, order: Order):
    """Buyurtmani barcha online haydovchilarga qayta yuborish."""
    result = await session.execute(
        select(Driver)
        .join(driver_routes, Driver.id == driver_routes.c.driver_id)
        .where(Driver.is_online == True)
        .where(Driver.status == DriverStatus.VERIFIED)
        .where(driver_routes.c.route_id == order.route_id)
    )
    drivers = result.scalars().all()

    route = await session.get(Route, order.route_id)
    route_text = f"{route.from_name} → {route.to_name}" if route else "—"
    user = await session.get(User, order.user_id)
    user_name = user.full_name if user else "—"

    for driver in drivers:
        driver_user = await session.get(User, driver.user_id)
        if driver_user:
            try:
                await bot.send_message(
                    driver_user.telegram_id,
                    f"🔔 <b>Buyurtma #{order.id}</b> — haydovchi kutilmoqda!\n\n"
                    f"🛣 {route_text}\n"
                    f"👥 {order.passenger_count} yo'lovchi\n"
                    f"💰 {order.price:,} so'm\n"
                    f"👤 {user_name}",
                    reply_markup=driver_order_action_kb(order.id),
                )
            except Exception:
                pass


async def _notify_drivers_upcoming(bot: Bot, session: AsyncSession, order: Order):
    """Rejalashtirilgan buyurtma haqida haydovchilarga oldindan xabar."""
    result = await session.execute(
        select(Driver)
        .join(driver_routes, Driver.id == driver_routes.c.driver_id)
        .where(Driver.is_online == True)
        .where(Driver.status == DriverStatus.VERIFIED)
        .where(driver_routes.c.route_id == order.route_id)
    )
    drivers = result.scalars().all()

    route = await session.get(Route, order.route_id)
    route_text = f"{route.from_name} → {route.to_name}" if route else "—"
    scheduled_time = order.scheduled_at.strftime("%H:%M") if order.scheduled_at else "—"

    for driver in drivers:
        driver_user = await session.get(User, driver.user_id)
        if driver_user:
            try:
                await bot.send_message(
                    driver_user.telegram_id,
                    f"🗓 <b>Rejalashtirilgan buyurtma!</b>\n\n"
                    f"🛣 {route_text}\n"
                    f"🕐 Vaqt: <b>{scheduled_time}</b>\n"
                    f"👥 {order.passenger_count} yo'lovchi\n"
                    f"💰 {order.price:,} so'm\n\n"
                    f"<i>15 daqiqadan so'ng faollashadi</i>",
                )
            except Exception:
                pass


async def run_scheduler(bot: Bot):
    """Asosiy scheduler loop — har 30 sekundda."""
    logger.info("Scheduler ishga tushdi!")
    while True:
        try:
            await check_expired_orders(bot)
            await check_scheduled_orders(bot)
        except Exception as e:
            logger.error(f"Scheduler xatolik: {e}")
        await asyncio.sleep(SCHEDULER_INTERVAL)
