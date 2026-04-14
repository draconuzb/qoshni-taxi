"""Admin commands — only for ADMIN_IDS users."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import admin_menu_kb, user_role_kb
from core.enums import UserRole, TripStatus
from core.models.user import User
from core.models import Driver, Trip, Booking
from infrastructure.config import settings

router = Router()


def is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.admin_ids


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("🔐 <b>Admin panel</b>", reply_markup=admin_menu_kb())


@router.message(Command("myid"))
async def cmd_myid(message: Message):
    await message.answer(f"🆔 <code>{message.from_user.id}</code>")


@router.callback_query(F.data == "admin:users")
async def admin_users(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        return

    result = await session.execute(select(User).order_by(User.id).limit(30))
    users = result.scalars().all()

    if not users:
        await callback.message.edit_text("👥 Foydalanuvchilar yo'q.", reply_markup=admin_menu_kb())
        return

    role_icons = {UserRole.USER: "👤", UserRole.DRIVER: "🚗"}
    text = "👥 <b>Foydalanuvchilar:</b>\n\n"
    for u in users:
        icon = role_icons.get(u.role, "👤")
        blocked = " 🚫" if u.is_blocked else ""
        text += f"{icon} <b>{u.full_name}</b> | {u.role}\n   <code>{u.telegram_id}</code>{blocked}\n\n"

    text += "<i>/role [telegram_id]</i>"
    await callback.message.edit_text(text, reply_markup=admin_menu_kb())


@router.message(Command("role"))
async def cmd_role(message: Message, session: AsyncSession):
    if not is_admin(message.from_user.id):
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Format: /role <telegram_id>")
        return

    try:
        telegram_id = int(args[1].strip())
    except ValueError:
        await message.answer("❌ ID raqam bo'lishi kerak!")
        return

    user = (await session.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
    if not user:
        await message.answer(f"❌ <code>{telegram_id}</code> topilmadi.")
        return

    await message.answer(
        f"👤 <b>{user.full_name}</b>\n🆔 <code>{user.telegram_id}</code>\n🏷 {user.role}",
        reply_markup=user_role_kb(user.id),
    )


@router.callback_query(F.data.startswith("admin:role:"))
async def set_role(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        return
    parts = callback.data.split(":")
    user_id = int(parts[2])
    new_role = parts[3]

    if new_role not in [r.value for r in UserRole]:
        await callback.answer("❌", show_alert=True)
        return

    user = await session.get(User, user_id)
    if not user:
        return

    user.role = UserRole(new_role)
    await session.commit()
    await callback.message.edit_text(f"✅ <b>{user.full_name}</b> → {user.role}", reply_markup=admin_menu_kb())


@router.callback_query(F.data.startswith("admin:block:"))
async def block_user(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        return
    user_id = int(callback.data.split(":")[-1])
    user = await session.get(User, user_id)
    if not user:
        return
    user.is_blocked = not user.is_blocked
    await session.commit()
    status = "🚫" if user.is_blocked else "✅"
    await callback.message.edit_text(f"{status} <b>{user.full_name}</b>", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        return
    total_users = await session.scalar(select(func.count(User.id))) or 0
    total_drivers = await session.scalar(select(func.count(Driver.id))) or 0
    total_trips = await session.scalar(select(func.count(Trip.id))) or 0
    departed = await session.scalar(select(func.count(Trip.id)).where(Trip.status == TripStatus.DEPARTED)) or 0
    total_bookings = await session.scalar(select(func.count(Booking.id))) or 0

    await callback.message.edit_text(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 {total_users}\n🚗 {total_drivers}\n🚐 {total_trips}\n✅ {departed}\n🎫 {total_bookings}",
        reply_markup=admin_menu_kb(),
    )
