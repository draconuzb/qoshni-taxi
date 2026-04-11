from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.role import RoleFilter
from bot.keyboards.inline import dispatcher_menu_kb
from core.enums import UserRole, OrderStatus, DriverStatus
from core.models import Order, Driver, Route
from core.models.user import User

router = Router()


@router.message(Command("dispatcher"))
async def cmd_dispatcher(message: Message, db_user: User | None):
    if not db_user or db_user.role != UserRole.DISPATCHER:
        await message.answer("⛔ Ruxsat yo'q!")
        return
    await message.answer(
        "📋 <b>Dispatcher paneli</b>",
        reply_markup=dispatcher_menu_kb(),
    )


@router.callback_query(F.data == "disp:refresh")
async def refresh_dispatcher(callback: CallbackQuery, db_user: User | None):
    if not db_user or db_user.role != UserRole.DISPATCHER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    await callback.message.edit_text(
        "📋 <b>Dispatcher paneli</b>",
        reply_markup=dispatcher_menu_kb(),
    )


@router.callback_query(F.data == "disp:active_orders")
async def active_orders(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.DISPATCHER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    result = await session.execute(
        select(Order)
        .where(Order.status.in_([OrderStatus.PENDING, OrderStatus.ACCEPTED, OrderStatus.IN_PROGRESS]))
        .order_by(Order.created_at.desc())
        .limit(20)
    )
    orders = result.scalars().all()

    if not orders:
        await callback.message.edit_text(
            "📋 <b>Faol buyurtmalar</b>\n\n"
            "Hozirda faol buyurtmalar yo'q.",
            reply_markup=dispatcher_menu_kb(),
        )
        return

    text = "📋 <b>Faol buyurtmalar:</b>\n\n"
    for order in orders:
        route = await session.get(Route, order.route_id)
        emoji = {"pending": "🟡", "accepted": "🟢", "in_progress": "🚕"}.get(order.status, "⚪")
        route_text = f"{route.from_name} → {route.to_name}" if route else "—"
        text += f"{emoji} <b>#{order.id}</b> | {route_text} | {order.passenger_count}👥 | {order.price:,} so'm\n"

    await callback.message.edit_text(text, reply_markup=dispatcher_menu_kb())


@router.callback_query(F.data == "disp:drivers")
async def list_drivers(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.DISPATCHER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    result = await session.execute(
        select(Driver, User)
        .join(User, Driver.user_id == User.id)
        .where(Driver.status == DriverStatus.VERIFIED)
    )
    rows = result.all()

    if not rows:
        await callback.message.edit_text(
            "🚗 <b>Haydovchilar</b>\n\nTasdiqlangan haydovchilar yo'q.",
            reply_markup=dispatcher_menu_kb(),
        )
        return

    text = "🚗 <b>Haydovchilar:</b>\n\n"
    for driver, user in rows:
        status = "🟢" if driver.is_online else "🔴"
        text += f"{status} <b>{user.full_name}</b> | {driver.car_model} | ⭐{driver.rating:.1f} | {driver.total_trips} safar\n"

    await callback.message.edit_text(text, reply_markup=dispatcher_menu_kb())


@router.callback_query(F.data == "disp:users")
async def list_users(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.DISPATCHER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    result = await session.execute(
        select(User).where(User.role == UserRole.USER).order_by(User.created_at.desc()).limit(20)
    )
    users = result.scalars().all()

    if not users:
        await callback.message.edit_text(
            "👥 <b>Yo'lovchilar</b>\n\nYo'lovchilar yo'q.",
            reply_markup=dispatcher_menu_kb(),
        )
        return

    text = "👥 <b>Yo'lovchilar:</b>\n\n"
    for u in users:
        text += f"👤 <b>{u.full_name}</b> | {u.phone or '—'}\n"

    await callback.message.edit_text(text, reply_markup=dispatcher_menu_kb())
