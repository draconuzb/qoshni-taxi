import logging
import math

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.manager_kb import driver_filter_kb, driver_list_kb, driver_detail_kb
from core.enums import UserRole, DriverStatus, TripStatus
from core.models import Driver, Trip, Route
from core.models.user import User

router = Router()
PAGE_SIZE = 8


@router.message(F.text == "🚗 Haydovchilar")
async def drivers_text(message: Message, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await message.answer("⛔ Ruxsat yo'q!")
        return
    pending = await session.scalar(
        select(func.count(Driver.id)).where(Driver.status == DriverStatus.PENDING_VERIFICATION)
    ) or 0
    await message.answer(
        "🚗 <b>Haydovchilar</b>\n\nFiltrni tanlang:",
        reply_markup=driver_filter_kb(pending),
    )


@router.callback_query(F.data.in_({"mgr:drivers", "mgr:pending"}))
async def show_driver_filters(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    pending = await session.scalar(
        select(func.count(Driver.id)).where(Driver.status == DriverStatus.PENDING_VERIFICATION)
    ) or 0

    if callback.data == "mgr:pending":
        await _show_driver_list(callback, session, "pending", 0)
        return

    await callback.message.edit_text(
        "🚗 <b>Haydovchilar</b>\n\nFiltrni tanlang:",
        reply_markup=driver_filter_kb(pending),
    )


@router.callback_query(F.data.startswith("mgr:drv_filter:"))
async def filter_drivers(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    filter_type = callback.data.split(":")[-1]
    await _show_driver_list(callback, session, filter_type, 0)


@router.callback_query(F.data.startswith("mgr:drv_page:"))
async def page_drivers(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    parts = callback.data.split(":")
    filter_type, page = parts[2], int(parts[3])
    await _show_driver_list(callback, session, filter_type, page)


async def _show_driver_list(callback: CallbackQuery, session: AsyncSession, filter_type: str, page: int):
    query = select(Driver, User).join(User, Driver.user_id == User.id)

    if filter_type == "pending":
        query = query.where(Driver.status == DriverStatus.PENDING_VERIFICATION)
    elif filter_type == "verified":
        query = query.where(Driver.status == DriverStatus.VERIFIED)
    elif filter_type == "blocked":
        query = query.where(Driver.status == DriverStatus.BLOCKED)

    total = await session.scalar(select(func.count()).select_from(query.subquery())) or 0
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))

    result = await session.execute(
        query.order_by(Driver.created_at.desc())
        .offset(page * PAGE_SIZE).limit(PAGE_SIZE)
    )
    rows = result.all()

    if not rows:
        await callback.message.edit_text(
            "🚗 Haydovchilar topilmadi.",
            reply_markup=driver_filter_kb(),
        )
        return

    await callback.message.edit_text(
        f"🚗 <b>Haydovchilar</b> ({total} ta)",
        reply_markup=driver_list_kb(rows, page, total_pages, filter_type),
    )


@router.callback_query(F.data.startswith("mgr:drv_detail:"))
async def show_driver_detail(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    driver_id = int(callback.data.split(":")[-1])
    driver = await session.get(Driver, driver_id)
    if not driver:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return

    user = await session.get(User, driver.user_id)
    route = await session.get(Route, driver.route_id) if driver.route_id else None

    total_trips = await session.scalar(
        select(func.count(Trip.id)).where(Trip.driver_id == driver_id)
    ) or 0
    completed_trips = await session.scalar(
        select(func.count(Trip.id)).where(
            and_(Trip.driver_id == driver_id, Trip.status == TripStatus.COMPLETED)
        )
    ) or 0

    route_text = f"{route.from_name} → {route.to_name}" if route else "biriktirilmagan"

    await callback.message.edit_text(
        f"🚗 <b>Haydovchi:</b> {user.full_name}\n\n"
        f"📞 {user.phone or '—'}\n"
        f"🆔 <code>{user.telegram_id}</code>\n"
        f"🚙 {driver.car_model} — {driver.car_color}\n"
        f"🔢 {driver.license_plate}\n"
        f"🛣 Yo'nalish: {route_text}\n"
        f"⭐ Reyting: {driver.rating:.1f}\n"
        f"🚐 Safarlar: {total_trips} (✅ {completed_trips})\n"
        f"📊 Holat: {driver.status}",
        reply_markup=driver_detail_kb(driver_id, driver.status),
    )


@router.callback_query(F.data.startswith("mgr:verify:"))
async def verify_driver(callback: CallbackQuery, session: AsyncSession, bot: Bot, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    driver_id = int(callback.data.split(":")[-1])
    driver = await session.get(Driver, driver_id)
    if not driver:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return
    driver.status = DriverStatus.VERIFIED
    await session.commit()
    user = await session.get(User, driver.user_id)
    try:
        await bot.send_message(user.telegram_id, "✅ Arizangiz tasdiqlandi! Endi safar e'lon qilishingiz mumkin.")
    except Exception:
        logging.exception("Failed to notify driver about verification")
    await callback.answer("✅ Tasdiqlandi!")
    await show_driver_detail(callback, session, db_user)


@router.callback_query(F.data.startswith("mgr:reject:"))
async def reject_driver(callback: CallbackQuery, session: AsyncSession, bot: Bot, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    driver_id = int(callback.data.split(":")[-1])
    driver = await session.get(Driver, driver_id)
    if not driver:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return
    driver.status = DriverStatus.REJECTED
    await session.commit()
    user = await session.get(User, driver.user_id)
    try:
        await bot.send_message(user.telegram_id, "❌ Haydovchi arizangiz rad etildi.")
    except Exception:
        logging.exception("Failed to notify driver about rejection")
    await callback.answer("❌ Rad etildi!")
    await show_driver_detail(callback, session, db_user)


@router.callback_query(F.data.startswith("mgr:block:"))
async def block_driver(callback: CallbackQuery, session: AsyncSession, bot: Bot, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    driver_id = int(callback.data.split(":")[-1])
    driver = await session.get(Driver, driver_id)
    if not driver:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return
    driver.status = DriverStatus.BLOCKED
    await session.commit()
    user = await session.get(User, driver.user_id)
    try:
        await bot.send_message(user.telegram_id, "🚫 Akkauntingiz bloklandi.")
    except Exception:
        logging.exception("Failed to notify driver about block")
    await callback.answer("🚫 Bloklandi!")
    await show_driver_detail(callback, session, db_user)


@router.callback_query(F.data.startswith("mgr:unblock:"))
async def unblock_driver(callback: CallbackQuery, session: AsyncSession, bot: Bot, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    driver_id = int(callback.data.split(":")[-1])
    driver = await session.get(Driver, driver_id)
    if not driver:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return
    driver.status = DriverStatus.VERIFIED
    await session.commit()
    user = await session.get(User, driver.user_id)
    try:
        await bot.send_message(user.telegram_id, "✅ Akkauntingiz blokdan chiqarildi.")
    except Exception:
        logging.exception("Failed to notify driver about unblock")
    await callback.answer("✅ Blokdan chiqarildi!")
    await show_driver_detail(callback, session, db_user)
