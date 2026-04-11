from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.reply_kb import manager_menu_kb
from core.enums import UserRole, DriverStatus, TripStatus
from core.models import Driver, Trip, Booking
from core.models.user import User

router = Router()


async def _get_dashboard_text(session: AsyncSession) -> str:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total_users = await session.scalar(select(func.count(User.id))) or 0
    total_drivers = await session.scalar(select(func.count(Driver.id))) or 0
    pending_drivers = await session.scalar(
        select(func.count(Driver.id)).where(Driver.status == DriverStatus.PENDING_VERIFICATION)
    ) or 0
    today_trips = await session.scalar(
        select(func.count(Trip.id)).where(Trip.created_at >= today_start)
    ) or 0
    today_completed = await session.scalar(
        select(func.count(Trip.id)).where(
            and_(Trip.status == TripStatus.COMPLETED, Trip.completed_at >= today_start)
        )
    ) or 0
    active_trips = await session.scalar(
        select(func.count(Trip.id)).where(
            Trip.status.in_([TripStatus.COLLECTING, TripStatus.DEPARTED])
        )
    ) or 0
    total_trips = await session.scalar(select(func.count(Trip.id))) or 0
    total_bookings = await session.scalar(select(func.count(Booking.id))) or 0

    return (
        "👨‍💼 <b>Manager Dashboard</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📅 <b>Bugun:</b>\n"
        f"   🚐 Safarlar: <b>{today_trips}</b>\n"
        f"   ✅ Yakunlangan: <b>{today_completed}</b>\n\n"
        "📊 <b>Hozir:</b>\n"
        f"   🚐 Faol safarlar: <b>{active_trips}</b>\n"
        f"   ⏳ Tasdiqlash kutmoqda: <b>{pending_drivers}</b>\n\n"
        "📈 <b>Umumiy:</b>\n"
        f"   👥 Foydalanuvchilar: <b>{total_users}</b>\n"
        f"   🚗 Haydovchilar: <b>{total_drivers}</b>\n"
        f"   🚐 Jami safarlar: <b>{total_trips}</b>\n"
        f"   🎫 Jami bronlar: <b>{total_bookings}</b>"
    )


@router.message(Command("manager"))
async def cmd_manager(message: Message, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await message.answer("⛔ Ruxsat yo'q!")
        return
    text = await _get_dashboard_text(session)
    await message.answer(text, reply_markup=manager_menu_kb())


@router.message(F.text == "📊 Ma'lumot va Statistika")
async def manager_stats_text(message: Message, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await message.answer("⛔ Ruxsat yo'q!")
        return
    text = await _get_dashboard_text(session)
    await message.answer(text)


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()
