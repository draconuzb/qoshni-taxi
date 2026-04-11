from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from infrastructure.config import settings


def manager_dashboard_kb(pending_count: int = 0) -> InlineKeyboardMarkup:
    pending_badge = f" ({pending_count})" if pending_count else ""
    buttons = []
    if settings.webapp_url:
        buttons.append([InlineKeyboardButton(
            text="🌐 Manager Panel (Web)",
            web_app=WebAppInfo(url=settings.webapp_url),
        )])
    buttons.extend([
        [InlineKeyboardButton(text=f"⏳ Tasdiqlash kutilmoqda{pending_badge}", callback_data="mgr:pending")],
        [
            InlineKeyboardButton(text="🚗 Haydovchilar", callback_data="mgr:drivers"),
            InlineKeyboardButton(text="🛣 Yo'nalishlar", callback_data="mgr:routes"),
        ],
        [
            InlineKeyboardButton(text="🚐 Safarlar", callback_data="mgr:trips"),
            InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="mgr:users"),
        ],
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="mgr:dashboard")],
        [InlineKeyboardButton(text="◀️ Asosiy menyu", callback_data="menu:main")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ── Drivers ───────────────────────────────────────────────────────────────────

def driver_filter_kb(pending_count: int = 0) -> InlineKeyboardMarkup:
    pending_badge = f" ({pending_count})" if pending_count else ""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⏳ Kutilmoqda{pending_badge}", callback_data="mgr:drv_filter:pending")],
        [
            InlineKeyboardButton(text="✅ Tasdiqlangan", callback_data="mgr:drv_filter:verified"),
            InlineKeyboardButton(text="🚫 Bloklangan", callback_data="mgr:drv_filter:blocked"),
        ],
        [InlineKeyboardButton(text="📊 Barcha haydovchilar", callback_data="mgr:drv_filter:all")],
        [InlineKeyboardButton(text="◀️ Dashboard", callback_data="mgr:dashboard")],
    ])


def driver_detail_kb(driver_id: int, status: str) -> InlineKeyboardMarkup:
    buttons = []
    if status == "pending_verification":
        buttons.append([
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"mgr:verify:{driver_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"mgr:reject:{driver_id}"),
        ])
    elif status == "verified":
        buttons.append([InlineKeyboardButton(text="🚫 Bloklash", callback_data=f"mgr:block:{driver_id}")])
    elif status == "blocked":
        buttons.append([InlineKeyboardButton(text="🔓 Blokdan chiqarish", callback_data=f"mgr:unblock:{driver_id}")])

    buttons.append([
        InlineKeyboardButton(text="🚐 Safarlari", callback_data=f"mgr:drv_trips:{driver_id}"),
    ])
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="mgr:drivers")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def driver_list_kb(drivers: list, page: int, total_pages: int, filter_type: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for driver, user in drivers:
        builder.button(
            text=f"🚗 {user.full_name} | ⭐{driver.rating:.1f}",
            callback_data=f"mgr:drv_detail:{driver.id}",
        )
    builder.adjust(1)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"mgr:drv_page:{filter_type}:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"mgr:drv_page:{filter_type}:{page + 1}"))
    if nav:
        builder.row(*nav)

    builder.row(InlineKeyboardButton(text="◀️ Filtrlar", callback_data="mgr:drivers"))
    return builder.as_markup()


# ── Trips ─────────────────────────────────────────────────────────────────────

def trip_filter_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟡 Joy to'planyapti", callback_data="mgr:trip_filter:collecting"),
            InlineKeyboardButton(text="🚀 Yo'lda", callback_data="mgr:trip_filter:departed"),
        ],
        [
            InlineKeyboardButton(text="✅ Yakunlangan", callback_data="mgr:trip_filter:completed"),
            InlineKeyboardButton(text="❌ Bekor qilingan", callback_data="mgr:trip_filter:cancelled"),
        ],
        [InlineKeyboardButton(text="📋 Barcha safarlar", callback_data="mgr:trip_filter:all")],
        [InlineKeyboardButton(text="◀️ Dashboard", callback_data="mgr:dashboard")],
    ])


def trip_list_kb(trips: list, page: int, total_pages: int, filter_type: str) -> InlineKeyboardMarkup:
    status_icons = {"collecting": "🟡", "departed": "🚀", "completed": "✅", "cancelled": "❌"}
    builder = InlineKeyboardBuilder()
    for trip in trips:
        icon = status_icons.get(trip.status, "📋")
        route = trip.route
        builder.button(
            text=f"{icon} #{trip.id} {route.from_name}→{route.to_name} | {trip.booked_seats}/{trip.total_seats}",
            callback_data=f"mgr:trip_detail:{trip.id}",
        )
    builder.adjust(1)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"mgr:trip_page:{filter_type}:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"mgr:trip_page:{filter_type}:{page + 1}"))
    if nav:
        builder.row(*nav)

    builder.row(InlineKeyboardButton(text="◀️ Filtrlar", callback_data="mgr:trips"))
    return builder.as_markup()


def trip_detail_kb(trip_id: int, status: str) -> InlineKeyboardMarkup:
    buttons = []
    if status in ("collecting", "departed"):
        buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"mgr:trip_cancel:{trip_id}")])
    buttons.append([InlineKeyboardButton(text="🚗 Haydovchi", callback_data=f"mgr:trip_driver:{trip_id}")])
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="mgr:trips")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ── Routes ────────────────────────────────────────────────────────────────────

def route_list_kb(routes: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for route in routes:
        status = "✅" if route.is_active else "⏸"
        builder.button(
            text=f"{status} {route.from_name} → {route.to_name} | {route.price:,}",
            callback_data=f"mgr:route_detail:{route.id}",
        )
    builder.adjust(1)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"mgr:route_page:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"mgr:route_page:{page + 1}"))
    if nav:
        builder.row(*nav)

    builder.row(InlineKeyboardButton(text="◀️ Dashboard", callback_data="mgr:dashboard"))
    return builder.as_markup()


def route_detail_kb(route_id: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle_text = "⏸ To'xtatish" if is_active else "▶️ Faollashtirish"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚗 Haydovchilari", callback_data=f"mgr:route_drivers:{route_id}")],
        [InlineKeyboardButton(text="✏️ Narxni o'zgartirish", callback_data=f"mgr:route_edit_price:{route_id}")],
        [
            InlineKeyboardButton(text=toggle_text, callback_data=f"mgr:route_toggle:{route_id}"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"mgr:route_delete:{route_id}"),
        ],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="mgr:routes")],
    ])


# ── Users ─────────────────────────────────────────────────────────────────────

def user_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Ism bo'yicha qidirish", callback_data="mgr:user_search_name")],
        [InlineKeyboardButton(text="📞 Telefon bo'yicha qidirish", callback_data="mgr:user_search_phone")],
        [InlineKeyboardButton(text="👥 Oxirgi foydalanuvchilar", callback_data="mgr:user_recent")],
        [InlineKeyboardButton(text="◀️ Dashboard", callback_data="mgr:dashboard")],
    ])


def user_list_kb(users: list, page: int, total_pages: int, source: str = "recent") -> InlineKeyboardMarkup:
    role_icons = {"user": "👤", "driver": "🚗", "dispatcher": "📋", "manager": "👨‍💼"}
    builder = InlineKeyboardBuilder()
    for u in users:
        icon = role_icons.get(u.role, "👤")
        blocked = " 🚫" if u.is_blocked else ""
        builder.button(
            text=f"{icon} {u.full_name}{blocked}",
            callback_data=f"mgr:user_detail:{u.id}",
        )
    builder.adjust(1)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"mgr:user_page:{source}:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"mgr:user_page:{source}:{page + 1}"))
    if nav:
        builder.row(*nav)

    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data="mgr:users"))
    return builder.as_markup()


def user_detail_kb(user_id: int, is_blocked: bool) -> InlineKeyboardMarkup:
    block_btn = (
        InlineKeyboardButton(text="🔓 Blokdan chiqarish", callback_data=f"mgr:user_unblock:{user_id}")
        if is_blocked
        else InlineKeyboardButton(text="🚫 Bloklash", callback_data=f"mgr:user_block:{user_id}")
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎫 Bronlari", callback_data=f"mgr:user_bookings:{user_id}")],
        [block_btn],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="mgr:users")],
    ])
