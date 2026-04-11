import math

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.keyboards.manager_kb import order_filter_kb, order_list_kb, order_detail_kb
from core.enums import UserRole, OrderStatus
from core.models import Order, Driver
from core.models.user import User

router = Router()

PAGE_SIZE = 8


def _order_filter_query(filter_type: str):
    base = select(Order).options(selectinload(Order.route))
    if filter_type == "pending":
        return base.where(Order.status == OrderStatus.PENDING)
    elif filter_type == "accepted":
        return base.where(Order.status == OrderStatus.ACCEPTED)
    elif filter_type == "in_progress":
        return base.where(Order.status == OrderStatus.IN_PROGRESS)
    elif filter_type == "completed":
        return base.where(Order.status == OrderStatus.COMPLETED)
    elif filter_type == "cancelled":
        return base.where(Order.status == OrderStatus.CANCELLED)
    elif filter_type == "expired":
        return base.where(Order.status == OrderStatus.EXPIRED)
    return base


@router.callback_query(F.data == "mgr:orders")
async def order_filters(callback: CallbackQuery, db_user: User | None):
    await callback.answer()
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
    await callback.message.edit_text(
        "📋 <b>Buyurtmalar</b>\n\nFiltrni tanlang:",
        reply_markup=order_filter_kb(),
    )


@router.callback_query(F.data.startswith("mgr:ord_filter:"))
async def order_list_filtered(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    await callback.answer()
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
    filter_type = callback.data.split(":")[-1]
    await _show_order_list(callback, session, filter_type, 0)


@router.callback_query(F.data.startswith("mgr:ord_page:"))
async def order_list_page(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    await callback.answer()
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
    parts = callback.data.split(":")
    filter_type = parts[2]
    page = int(parts[3])
    await _show_order_list(callback, session, filter_type, page)


async def _show_order_list(callback: CallbackQuery, session: AsyncSession, filter_type: str, page: int):
    query = _order_filter_query(filter_type).order_by(Order.created_at.desc())

    count_q = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_q) or 0
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = min(page, total_pages - 1)

    result = await session.execute(query.offset(page * PAGE_SIZE).limit(PAGE_SIZE))
    orders = result.scalars().all()

    filter_names = {
        "pending": "🟡 Kutilmoqda", "accepted": "🟢 Qabul qilingan",
        "in_progress": "🚕 Yo'lda", "completed": "✅ Bajarilgan",
        "cancelled": "❌ Bekor qilingan", "expired": "⏰ Muddati o'tgan",
        "all": "📋 Barchasi",
    }
    title = filter_names.get(filter_type, "Buyurtmalar")

    if not orders:
        await callback.message.edit_text(
            f"📋 <b>{title}</b>\n\nBuyurtmalar topilmadi.",
            reply_markup=order_filter_kb(),
        )
        return

    await callback.message.edit_text(
        f"📋 <b>{title}</b> ({total} ta)",
        reply_markup=order_list_kb(orders, page, total_pages, filter_type),
    )


@router.callback_query(F.data.startswith("mgr:ord_detail:"))
async def order_detail(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    await callback.answer()
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
    order_id = int(callback.data.split(":")[-1])
    order = await session.get(Order, order_id, options=[
        selectinload(Order.route), selectinload(Order.user), selectinload(Order.driver),
    ])
    if not order:
        await callback.answer("Buyurtma topilmadi", show_alert=True)
        return

    status_text = {
        "pending": "🟡 Kutilmoqda", "accepted": "🟢 Qabul qilingan",
        "driver_arrived": "📍 Haydovchi yetib keldi", "in_progress": "🚕 Yo'lda",
        "completed": "✅ Bajarilgan", "cancelled": "❌ Bekor qilingan",
        "scheduled": "🗓 Rejalashtirilgan", "expired": "⏰ Muddati o'tgan",
    }.get(order.status, order.status)

    route_text = f"{order.route.from_name} → {order.route.to_name}" if order.route else "—"

    driver_text = "—"
    if order.driver:
        driver_user = await session.get(User, order.driver.user_id)
        driver_text = f"{driver_user.full_name if driver_user else '—'} ({order.driver.car_model})"

    user_text = order.user.full_name if order.user else "—"
    user_phone = order.user.phone if order.user else "—"

    text = (
        f"📋 <b>Buyurtma #{order.id}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📊 Holat: {status_text}\n"
        f"🛣 Yo'nalish: <b>{route_text}</b>\n"
        f"👥 Yo'lovchilar: <b>{order.passenger_count}</b>\n"
        f"💰 Narx: <b>{order.price:,} so'm</b>\n\n"
        f"👤 Yo'lovchi: <b>{user_text}</b>\n"
        f"📞 Telefon: {user_phone}\n"
        f"🚗 Haydovchi: <b>{driver_text}</b>\n\n"
        f"📅 Yaratilgan: {order.created_at.strftime('%d.%m.%Y %H:%M') if order.created_at else '—'}\n"
        f"✅ Qabul: {order.accepted_at.strftime('%d.%m.%Y %H:%M') if order.accepted_at else '—'}\n"
        f"🏁 Tugagan: {order.completed_at.strftime('%d.%m.%Y %H:%M') if order.completed_at else '—'}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=order_detail_kb(order.id, order.status),
    )


@router.callback_query(F.data.startswith("mgr:ord_cancel:"))
async def cancel_order(callback: CallbackQuery, session: AsyncSession, bot: Bot, db_user: User | None):
    await callback.answer()
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
    order_id = int(callback.data.split(":")[-1])
    order = await session.get(Order, order_id, options=[selectinload(Order.user)])
    if not order:
        await callback.answer("Buyurtma topilmadi", show_alert=True)
        return

    order.status = OrderStatus.CANCELLED
    await session.commit()

    await callback.answer("❌ Buyurtma bekor qilindi")

    if order.user:
        try:
            await bot.send_message(
                order.user.telegram_id,
                f"❌ Buyurtma #{order.id} manager tomonidan bekor qilindi.",
            )
        except Exception:
            pass

    # Refresh detail
    callback.data = f"mgr:ord_detail:{order_id}"
    await order_detail(callback, session, db_user)


@router.callback_query(F.data.startswith("mgr:ord_user:"))
async def order_user_detail(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    await callback.answer()
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
    order_id = int(callback.data.split(":")[-1])
    order = await session.get(Order, order_id)
    if not order:
        await callback.answer("Buyurtma topilmadi", show_alert=True)
        return
    # Redirect to user detail
    callback.data = f"mgr:user_detail:{order.user_id}"
    from bot.handlers.manager.users import user_detail
    await user_detail(callback, session, db_user)


@router.callback_query(F.data.startswith("mgr:ord_driver:"))
async def order_driver_detail(callback: CallbackQuery, session: AsyncSession, db_user: User | None):
    await callback.answer()
    if not db_user or db_user.role != UserRole.MANAGER:
        await callback.answer("Ruxsat yo'q!", show_alert=True)
        return
    order_id = int(callback.data.split(":")[-1])
    order = await session.get(Order, order_id)
    if not order or not order.driver_id:
        await callback.answer("Haydovchi topilmadi", show_alert=True)
        return
    callback.data = f"mgr:drv_detail:{order.driver_id}"
    from bot.handlers.manager.drivers import driver_detail
    await driver_detail(callback, session, db_user)
