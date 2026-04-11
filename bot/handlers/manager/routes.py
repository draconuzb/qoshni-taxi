import math

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.manager_kb import route_list_kb, route_detail_kb, manager_dashboard_kb
from core.enums import UserRole, TripStatus
from core.models import Route, Driver, Trip
from core.models.user import User

router = Router()
PAGE_SIZE = 8


class RoutePriceEditState(StatesGroup):
    waiting_price = State()


@router.message(F.text == "🛣 Yo'nalishlar")
async def routes_text(message: Message, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await message.answer("⛔ Ruxsat yo'q!")
        return
    await _show_routes_page_msg(message, session, 0)


async def _show_routes_page_msg(message: Message, session: AsyncSession, page: int):
    from sqlalchemy import func as sqfunc
    total = await session.scalar(select(func.count(Route.id))) or 0
    import math as m
    total_pages = max(1, m.ceil(total / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))

    result = await session.execute(
        select(Route).order_by(Route.id)
        .offset(page * PAGE_SIZE).limit(PAGE_SIZE)
    )
    routes = result.scalars().all()

    if not routes:
        await message.answer("🛣 Yo'nalishlar yo'q.\nWeb panel orqali yangi yo'nalish qo'shing.")
        return

    await message.answer(
        f"🛣 <b>Yo'nalishlar</b> ({total} ta)",
        reply_markup=route_list_kb(routes, page, total_pages),
    )


@router.callback_query(F.data == "mgr:routes")
async def show_routes(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    await _show_routes_page(callback, session, 0)


@router.callback_query(F.data.startswith("mgr:route_page:"))
async def route_page(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    page = int(callback.data.split(":")[-1])
    await _show_routes_page(callback, session, page)


async def _show_routes_page(callback: CallbackQuery, session: AsyncSession, page: int):
    total = await session.scalar(select(func.count(Route.id))) or 0
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))

    result = await session.execute(
        select(Route).order_by(Route.id)
        .offset(page * PAGE_SIZE).limit(PAGE_SIZE)
    )
    routes = result.scalars().all()

    if not routes:
        await callback.message.edit_text(
            "🛣 Yo'nalishlar yo'q.\nWeb panel orqali yangi yo'nalish qo'shing.",
            reply_markup=manager_dashboard_kb(),
        )
        return

    await callback.message.edit_text(
        f"🛣 <b>Yo'nalishlar</b> ({total} ta)",
        reply_markup=route_list_kb(routes, page, total_pages),
    )


@router.callback_query(F.data.startswith("mgr:route_detail:"))
async def show_route_detail(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    route_id = int(callback.data.split(":")[-1])
    route = await session.get(Route, route_id)
    if not route:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return

    driver_count = await session.scalar(
        select(func.count(Driver.id)).where(Driver.route_id == route_id)
    ) or 0
    total_trips = await session.scalar(
        select(func.count(Trip.id)).where(Trip.route_id == route_id)
    ) or 0
    completed_trips = await session.scalar(
        select(func.count(Trip.id)).where(
            and_(Trip.route_id == route_id, Trip.status == TripStatus.COMPLETED)
        )
    ) or 0

    await callback.message.edit_text(
        f"🛣 <b>{route.from_name} → {route.to_name}</b>\n\n"
        f"💰 Narx: <b>{route.price:,} so'm</b>\n"
        f"📊 Holat: {'✅ Faol' if route.is_active else '⏸ Toxtatilgan'}\n"
        f"🚗 Haydovchilar: {driver_count}\n"
        f"🚐 Safarlar: {total_trips} (✅ {completed_trips})",
        reply_markup=route_detail_kb(route_id, route.is_active),
    )


@router.callback_query(F.data.startswith("mgr:route_toggle:"))
async def toggle_route(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    route_id = int(callback.data.split(":")[-1])
    route = await session.get(Route, route_id)
    if not route:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return
    route.is_active = not route.is_active
    await session.commit()
    await callback.answer("✅" if route.is_active else "⏸")
    await show_route_detail(callback, session, db_user)


@router.callback_query(F.data.startswith("mgr:route_delete:"))
async def delete_route(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    route_id = int(callback.data.split(":")[-1])
    route = await session.get(Route, route_id)
    if not route:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return
    await session.delete(route)
    await session.commit()
    await callback.answer("🗑 O'chirildi!")
    await show_routes(callback, session, db_user)


@router.callback_query(F.data.startswith("mgr:route_edit_price:"))
async def start_price_edit(callback: CallbackQuery, state: FSMContext, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    route_id = int(callback.data.split(":")[-1])
    await state.update_data(edit_route_id=route_id)
    await callback.message.edit_text(
        "✏️ Yangi narxni kiriting (so'mda):\n<i>Masalan: 50000</i>"
    )
    await state.set_state(RoutePriceEditState.waiting_price)


@router.message(RoutePriceEditState.waiting_price)
async def process_price_edit(message: Message, session: AsyncSession, state: FSMContext, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await message.answer("⛔ Ruxsat yo'q!")
        return
    try:
        price = int(message.text.strip().replace(" ", "").replace(",", ""))
        if price <= 0:
            raise ValueError
    except (ValueError, AttributeError):
        await message.answer("❌ Noto'g'ri raqam! Masalan: 50000")
        return

    data = await state.get_data()
    route = await session.get(Route, data["edit_route_id"])
    if route:
        route.price = price
        await session.commit()
    await state.clear()
    await message.answer(f"✅ Narx {price:,} so'mga o'zgartirildi.")


@router.callback_query(F.data.startswith("mgr:route_drivers:"))
async def show_route_drivers(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return
    route_id = int(callback.data.split(":")[-1])
    result = await session.execute(
        select(Driver, User).join(User, Driver.user_id == User.id)
        .where(Driver.route_id == route_id).limit(20)
    )
    rows = result.all()
    if not rows:
        await callback.answer("Bu yo'nalishda haydovchi yo'q.", show_alert=True)
        return

    text = "🚗 <b>Yo'nalish haydovchilari:</b>\n\n"
    for driver, user in rows:
        text += f"  🚗 {user.full_name} | {driver.car_model} | ⭐{driver.rating:.1f}\n"

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"mgr:route_detail:{route_id}")],
        ]),
    )
