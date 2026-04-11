import logging
import math

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.keyboards.manager_kb import trip_filter_kb, trip_list_kb, trip_detail_kb
from core.enums import UserRole, TripStatus, TripDirection, BookingStatus
from core.models import Trip, Booking, Driver
from core.models.route import Route
from core.models.user import User

router = Router()
PAGE_SIZE = 8


@router.message(F.text == "🚐 Safarlar")
async def trips_text(message: Message, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await message.answer("⛔ Ruxsat yo'q!")
        return
    await message.answer(
        "🚐 <b>Safarlar</b>\n\nFiltrni tanlang:",
        reply_markup=trip_filter_kb(),
    )


@router.callback_query(F.data == "mgr:trips")
async def show_trip_filters(callback: CallbackQuery, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    await callback.message.edit_text(
        "🚐 <b>Safarlar</b>\n\nFiltrni tanlang:",
        reply_markup=trip_filter_kb(),
    )


@router.callback_query(F.data.startswith("mgr:trip_filter:"))
async def filter_trips(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    filter_type = callback.data.split(":")[-1]
    await _show_trip_list(callback, session, filter_type, 0)


@router.callback_query(F.data.startswith("mgr:trip_page:"))
async def page_trips(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    parts = callback.data.split(":")
    filter_type, page = parts[2], int(parts[3])
    await _show_trip_list(callback, session, filter_type, page)


async def _show_trip_list(callback: CallbackQuery, session: AsyncSession, filter_type: str, page: int):
    query = select(Trip).options(selectinload(Trip.route))

    status_map = {
        "collecting": TripStatus.COLLECTING,
        "departed": TripStatus.DEPARTED,
        "completed": TripStatus.COMPLETED,
        "cancelled": TripStatus.CANCELLED,
    }
    if filter_type in status_map:
        query = query.where(Trip.status == status_map[filter_type])

    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))

    result = await session.execute(
        query.order_by(Trip.created_at.desc())
        .offset(page * PAGE_SIZE).limit(PAGE_SIZE)
    )
    trips = result.scalars().all()

    if not trips:
        await callback.message.edit_text(
            "🚐 Safarlar topilmadi.",
            reply_markup=trip_filter_kb(),
        )
        return

    await callback.message.edit_text(
        f"🚐 <b>Safarlar</b> ({total} ta)",
        reply_markup=trip_list_kb(trips, page, total_pages, filter_type),
    )


@router.callback_query(F.data.startswith("mgr:trip_detail:"))
async def show_trip_detail(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    trip_id = int(callback.data.split(":")[-1])
    trip = await session.get(Trip, trip_id)
    if not trip:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return

    await session.refresh(trip, ["route", "driver", "bookings"])
    await session.refresh(trip.driver, ["user"])
    for b in trip.bookings:
        await session.refresh(b, ["user"])

    route = trip.route
    if trip.direction == TripDirection.A_TO_B:
        dir_text = f"{route.from_name} → {route.to_name}"
    else:
        dir_text = f"{route.to_name} → {route.from_name}"

    status_names = {
        "collecting": "🟡 Joy to'planyapti",
        "departed": "🚀 Yo'lda",
        "completed": "✅ Yakunlangan",
        "cancelled": "❌ Bekor qilingan",
    }

    active_bookings = [b for b in trip.bookings if b.status in (BookingStatus.ACTIVE, "active")]
    passengers = "\n".join(f"  👤 {b.user.full_name}" for b in active_bookings) or "  — yo'q"

    await callback.message.edit_text(
        f"🚐 <b>Safar #{trip.id}</b>\n\n"
        f"🛣 {dir_text}\n"
        f"🚗 Haydovchi: {trip.driver.user.full_name}\n"
        f"👥 {trip.booked_seats}/{trip.total_seats} joy band\n"
        f"💰 {trip.price_per_seat:,} so'm / kishi\n"
        f"📊 Holat: {status_names.get(trip.status, trip.status)}\n"
        f"📅 Yaratilgan: {trip.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"<b>Yo'lovchilar:</b>\n{passengers}",
        reply_markup=trip_detail_kb(trip_id, trip.status),
    )


@router.callback_query(F.data.startswith("mgr:trip_cancel:"))
async def cancel_trip(callback: CallbackQuery, session: AsyncSession, bot: Bot, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    trip_id = int(callback.data.split(":")[-1])
    trip = await session.get(Trip, trip_id)
    if not trip:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return

    trip.status = TripStatus.CANCELLED
    await session.commit()
    await session.refresh(trip, ["route", "bookings", "driver"])
    await session.refresh(trip.driver, ["user"])
    for b in trip.bookings:
        await session.refresh(b, ["user"])
        if b.status in (BookingStatus.ACTIVE, "active"):
            b.status = BookingStatus.CANCELLED
    await session.commit()

    route = trip.route
    if trip.direction == TripDirection.A_TO_B:
        dir_text = f"{route.from_name} → {route.to_name}"
    else:
        dir_text = f"{route.to_name} → {route.from_name}"

    # Notify driver
    try:
        await bot.send_message(
            trip.driver.user.telegram_id,
            f"❌ Manager safar #{trip.id} ni bekor qildi.",
        )
    except Exception:
        logging.exception("Failed to notify driver about manager trip cancellation")

    # Notify passengers
    for b in trip.bookings:
        try:
            await bot.send_message(
                b.user.telegram_id,
                f"❌ <b>Safar bekor qilindi</b>\n🛣 {dir_text}",
            )
        except Exception:
            logging.exception("Failed to notify passenger about manager trip cancellation")

    await callback.answer("❌ Bekor qilindi!")
    await show_trip_detail(callback, session, db_user)


@router.callback_query(F.data.startswith("mgr:trip_driver:"))
async def trip_go_to_driver(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    trip_id = int(callback.data.split(":")[-1])
    trip = await session.get(Trip, trip_id)
    if not trip:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return
    # Reuse driver detail callback
    callback.data = f"mgr:drv_detail:{trip.driver_id}"
    from bot.handlers.manager.drivers import show_driver_detail
    await show_driver_detail(callback, session, db_user)
