"""Admin buyruqlari — faqat ADMIN_IDS dagi foydalanuvchilar uchun."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import admin_menu_kb, user_role_kb
from core.enums import UserRole
from core.models.user import User
from core.models.driver import Driver
from infrastructure.config import settings

router = Router()


def is_admin(telegram_id: int) -> bool:
    return telegram_id in settings.admin_ids


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Ruxsat yo'q!")
        return
    await message.answer(
        "🔐 <b>Admin panel</b>",
        reply_markup=admin_menu_kb(),
    )


@router.message(Command("myid"))
async def cmd_myid(message: Message):
    await message.answer(f"🆔 Sizning Telegram ID: <code>{message.from_user.id}</code>")


@router.callback_query(F.data == "admin:users")
async def admin_users(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    result = await session.execute(select(User).order_by(User.id).limit(30))
    users = result.scalars().all()

    if not users:
        await callback.message.edit_text(
            "👥 <b>Foydalanuvchilar</b>\n\nFoydalanuvchilar yo'q.",
            reply_markup=admin_menu_kb(),
        )
        return

    role_icons = {"user": "👤", "driver": "🚗", "dispatcher": "📋", "manager": "👨‍💼"}
    text = "👥 <b>Foydalanuvchilar:</b>\n\n"
    for u in users:
        icon = role_icons.get(u.role, "👤")
        blocked = " 🚫" if u.is_blocked else ""
        text += (
            f"{icon} <b>{u.full_name}</b> | {u.role}\n"
            f"   ID: <code>{u.telegram_id}</code>{blocked}\n\n"
        )

    text += "<i>Rolni o'zgartirish uchun /role [telegram_id] yuboring</i>"
    await callback.message.edit_text(text, reply_markup=admin_menu_kb())


@router.message(Command("role"))
async def cmd_role(message: Message, session: AsyncSession):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Ruxsat yo'q!")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Format: /role <telegram_id>")
        return

    try:
        telegram_id = int(args[1].strip())
    except ValueError:
        await message.answer("❌ Telegram ID raqam bo'lishi kerak!")
        return

    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if not user:
        await message.answer(f"❌ Telegram ID <code>{telegram_id}</code> topilmadi.")
        return

    role_icons = {"user": "👤", "driver": "🚗", "dispatcher": "📋", "manager": "👨‍💼"}
    icon = role_icons.get(user.role, "👤")

    await message.answer(
        f"👤 <b>{user.full_name}</b>\n"
        f"🆔 <code>{user.telegram_id}</code>\n"
        f"🏷 Hozirgi rol: {icon} {user.role}\n\n"
        "Yangi rolni tanlang:",
        reply_markup=user_role_kb(user.id),
    )


@router.callback_query(F.data.startswith("admin:role:"))
async def set_role(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    parts = callback.data.split(":")
    user_id = int(parts[2])
    new_role = parts[3]

    user = await session.get(User, user_id)
    if not user:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return

    user.role = UserRole(new_role)
    await session.commit()

    role_names = {
        UserRole.MANAGER: "👨‍💼 Manager",
        UserRole.DISPATCHER: "📋 Dispatcher",
        UserRole.USER: "👤 Foydalanuvchi",
        UserRole.DRIVER: "🚗 Haydovchi",
    }

    await callback.message.edit_text(
        f"✅ <b>{user.full_name}</b> — {role_names.get(user.role, user.role)} bo'ldi!",
        reply_markup=admin_menu_kb(),
    )


@router.callback_query(F.data.startswith("admin:block:"))
async def block_user(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    user_id = int(callback.data.split(":")[-1])
    user = await session.get(User, user_id)
    if not user:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return

    user.is_blocked = not user.is_blocked
    await session.commit()

    status = "bloklandi 🚫" if user.is_blocked else "blokdan chiqarildi ✅"
    await callback.message.edit_text(
        f"<b>{user.full_name}</b> {status}",
        reply_markup=admin_menu_kb(),
    )


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery, session: AsyncSession):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    from sqlalchemy import func
    from core.models import Driver, Trip, Booking
    from core.enums import TripStatus

    total_users = await session.scalar(select(func.count(User.id))) or 0
    total_drivers = await session.scalar(select(func.count(Driver.id))) or 0
    total_trips = await session.scalar(select(func.count(Trip.id))) or 0
    completed = await session.scalar(
        select(func.count(Trip.id)).where(Trip.status == TripStatus.COMPLETED)
    ) or 0
    total_bookings = await session.scalar(select(func.count(Booking.id))) or 0

    await callback.message.edit_text(
        f"📊 <b>Admin Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{total_users}</b>\n"
        f"🚗 Haydovchilar: <b>{total_drivers}</b>\n"
        f"🚐 Safarlar: <b>{total_trips}</b>\n"
        f"✅ Bajarilgan: <b>{completed}</b>\n"
        f"🎫 Bronlar: <b>{total_bookings}</b>",
        reply_markup=admin_menu_kb(),
    )


@router.callback_query(F.data == "admin:set_manager")
async def prompt_set_manager(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    await callback.message.edit_text(
        "👨‍💼 <b>Manager tayinlash</b>\n\n"
        "Foydalanuvchining Telegram ID sini yuboring:\n"
        "<code>/role 123456789</code>\n\n"
        "ID bilish uchun foydalanuvchi /myid buyrug'ini yuborsin.",
        reply_markup=admin_menu_kb(),
    )


@router.callback_query(F.data == "admin:set_dispatcher")
async def prompt_set_dispatcher(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    await callback.message.edit_text(
        "📋 <b>Dispatcher tayinlash</b>\n\n"
        "Foydalanuvchining Telegram ID sini yuboring:\n"
        "<code>/role 123456789</code>\n\n"
        "ID bilish uchun foydalanuvchi /myid buyrug'ini yuborsin.",
        reply_markup=admin_menu_kb(),
    )
