import logging
import math

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.manager_kb import user_menu_kb, user_list_kb, user_detail_kb
from core.enums import UserRole
from core.models import Booking, Route
from core.models.user import User

router = Router()
PAGE_SIZE = 8


class UserSearchState(StatesGroup):
    search_name = State()
    search_phone = State()


@router.message(F.text == "👥 Foydalanuvchilar")
async def users_text(message: Message, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await message.answer("⛔ Ruxsat yo'q!")
        return
    await message.answer(
        "👥 <b>Foydalanuvchilar</b>",
        reply_markup=user_menu_kb(),
    )


@router.callback_query(F.data == "mgr:users")
async def show_user_menu(callback: CallbackQuery, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    await callback.message.edit_text(
        "👥 <b>Foydalanuvchilar</b>",
        reply_markup=user_menu_kb(),
    )


@router.callback_query(F.data == "mgr:user_search_name")
async def start_search_name(callback: CallbackQuery, state: FSMContext, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    await callback.message.edit_text("🔍 Ismni kiriting:")
    await state.set_state(UserSearchState.search_name)


@router.message(UserSearchState.search_name)
async def process_search_name(message: Message, session: AsyncSession, state: FSMContext, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await message.answer("⛔ Ruxsat yo'q!")
        return
    query = message.text.strip()
    await state.clear()

    result = await session.execute(
        select(User).where(User.full_name.ilike(f"%{query}%"))
        .order_by(User.created_at.desc()).limit(20)
    )
    users = result.scalars().all()

    if not users:
        await message.answer("❌ Topilmadi.", reply_markup=user_menu_kb())
        return

    total_pages = max(1, math.ceil(len(users) / PAGE_SIZE))
    await message.answer(
        f"🔍 <b>Natijalar:</b> {len(users)} ta",
        reply_markup=user_list_kb(users[:PAGE_SIZE], 0, total_pages, "search"),
    )


@router.callback_query(F.data == "mgr:user_search_phone")
async def start_search_phone(callback: CallbackQuery, state: FSMContext, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    await callback.message.edit_text("📞 Telefon raqamni kiriting:")
    await state.set_state(UserSearchState.search_phone)


@router.message(UserSearchState.search_phone)
async def process_search_phone(message: Message, session: AsyncSession, state: FSMContext, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await message.answer("⛔ Ruxsat yo'q!")
        return
    query = message.text.strip()
    await state.clear()

    result = await session.execute(
        select(User).where(User.phone.ilike(f"%{query}%"))
        .order_by(User.created_at.desc()).limit(20)
    )
    users = result.scalars().all()

    if not users:
        await message.answer("❌ Topilmadi.", reply_markup=user_menu_kb())
        return

    total_pages = max(1, math.ceil(len(users) / PAGE_SIZE))
    await message.answer(
        f"📞 <b>Natijalar:</b> {len(users)} ta",
        reply_markup=user_list_kb(users[:PAGE_SIZE], 0, total_pages, "search"),
    )


@router.callback_query(F.data == "mgr:user_recent")
async def show_recent_users(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    await _show_user_page(callback, session, 0)


@router.callback_query(F.data.startswith("mgr:user_page:"))
async def user_page(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    parts = callback.data.split(":")
    page = int(parts[-1])
    await _show_user_page(callback, session, page)


async def _show_user_page(callback: CallbackQuery, session: AsyncSession, page: int):
    total = await session.scalar(select(func.count(User.id))) or 0
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))

    result = await session.execute(
        select(User).order_by(User.created_at.desc())
        .offset(page * PAGE_SIZE).limit(PAGE_SIZE)
    )
    users = result.scalars().all()

    await callback.message.edit_text(
        f"👥 <b>Foydalanuvchilar</b> ({total} ta)",
        reply_markup=user_list_kb(users, page, total_pages, "recent"),
    )


@router.callback_query(F.data.startswith("mgr:user_detail:"))
async def show_user_detail(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    user_id = int(callback.data.split(":")[-1])
    user = await session.get(User, user_id)
    if not user:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return

    total_bookings = await session.scalar(
        select(func.count(Booking.id)).where(Booking.user_id == user_id)
    ) or 0

    route_text = ""
    if user.route_id:
        route = await session.get(Route, user.route_id)
        if route:
            route_text = f"\n🛣 Yo'nalish: {route.from_name} → {route.to_name}"
            if user.direction:
                route_text += f" ({user.direction})"

    role_icons = {"user": "👤", "driver": "🚗", "dispatcher": "📋", "manager": "👨‍💼"}
    icon = role_icons.get(user.role, "👤")

    await callback.message.edit_text(
        f"{icon} <b>{user.full_name}</b>\n\n"
        f"📞 {user.phone or '—'}\n"
        f"🆔 <code>{user.telegram_id}</code>\n"
        f"🏷 Rol: {user.role}"
        f"{route_text}\n"
        f"🎫 Bronlar: {total_bookings}\n"
        f"{'🚫 BLOKLANGAN' if user.is_blocked else ''}\n"
        f"📅 Ro'yxatdan: {user.created_at.strftime('%d.%m.%Y')}",
        reply_markup=user_detail_kb(user_id, user.is_blocked),
    )


@router.callback_query(F.data.startswith("mgr:user_block:"))
async def block_user(callback: CallbackQuery, session: AsyncSession, bot: Bot, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    user_id = int(callback.data.split(":")[-1])
    user = await session.get(User, user_id)
    if not user:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return
    user.is_blocked = True
    await session.commit()
    try:
        await bot.send_message(user.telegram_id, "🚫 Akkauntingiz bloklandi.")
    except Exception:
        logging.exception("Failed to notify user about block")
    await callback.answer("🚫 Bloklandi!")
    await show_user_detail(callback, session, db_user)


@router.callback_query(F.data.startswith("mgr:user_unblock:"))
async def unblock_user(callback: CallbackQuery, session: AsyncSession, bot: Bot, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    user_id = int(callback.data.split(":")[-1])
    user = await session.get(User, user_id)
    if not user:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return
    user.is_blocked = False
    await session.commit()
    try:
        await bot.send_message(user.telegram_id, "✅ Akkauntingiz blokdan chiqarildi.")
    except Exception:
        logging.exception("Failed to notify user about unblock")
    await callback.answer("✅ Blokdan chiqarildi!")
    await show_user_detail(callback, session, db_user)
