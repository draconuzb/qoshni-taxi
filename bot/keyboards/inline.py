from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.locations import REGIONS


# ═══════════════════════════════════════════
#  ASOSIY MENYU
# ═══════════════════════════════════════════

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚕 Taxi chaqirish", callback_data="menu:order")],
        [InlineKeyboardButton(text="🚐 Mavjud triplar", callback_data="menu:trips")],
        [
            InlineKeyboardButton(text="📋 Buyurtmalarim", callback_data="menu:my_orders"),
            InlineKeyboardButton(text="👤 Profil", callback_data="menu:profile"),
        ],
        [InlineKeyboardButton(text="ℹ️ Yordam", callback_data="menu:help")],
    ])


def back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Asosiy menyu", callback_data="menu:main")],
    ])


# ═══════════════════════════════════════════
#  HAYDOVCHI MENYUSI
# ═══════════════════════════════════════════

def driver_menu_kb(is_online: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if is_online:
        rows.append([InlineKeyboardButton(text="🔴 Offline bo'lish", callback_data="driver:go_offline")])
    else:
        rows.append([InlineKeyboardButton(text="🟢 Online bo'lish", callback_data="driver:go_online")])
    rows.extend([
        [InlineKeyboardButton(text="🚐 Yangi safar e'lon qilish", callback_data="driver:open_trip")],
        [InlineKeyboardButton(text="📋 Faol safar", callback_data="driver:active_trip")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="driver:stats")],
        [InlineKeyboardButton(text="◀️ Asosiy menyu", callback_data="menu:main")],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def driver_order_action_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"order:accept:{order_id}"),
            InlineKeyboardButton(text="⏭ Keyingisi", callback_data=f"order:skip:{order_id}"),
        ],
    ])


def driver_trip_kb(order_id: int, status: str) -> InlineKeyboardMarkup:
    buttons = []
    if status == "accepted":
        buttons.append([InlineKeyboardButton(text="📍 Yetib keldim", callback_data=f"trip:arrived:{order_id}")])
    elif status == "driver_arrived":
        buttons.append([InlineKeyboardButton(text="🚕 Safarni boshlash", callback_data=f"trip:start:{order_id}")])
    elif status == "in_progress":
        buttons.append([InlineKeyboardButton(text="🏁 Safarni tugatish", callback_data=f"trip:end:{order_id}")])
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"trip:cancel:{order_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def driver_reg_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚗 Haydovchi bo'lish", callback_data="driver:register")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="menu:main")],
    ])


# ═══════════════════════════════════════════
#  BUYURTMA
# ═══════════════════════════════════════════

def routes_kb(routes: list, prefix: str = "route:select") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for route in routes:
        name_part = f"{route.name}: " if route.name else ""
        builder.button(
            text=f"{name_part}{route.from_name} ↔ {route.to_name}",
            callback_data=f"{prefix}:{route.id}",
        )
    builder.button(text="◀️ Orqaga", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def passenger_count_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣", callback_data="passengers:1"),
            InlineKeyboardButton(text="2️⃣", callback_data="passengers:2"),
            InlineKeyboardButton(text="3️⃣", callback_data="passengers:3"),
            InlineKeyboardButton(text="4️⃣", callback_data="passengers:4"),
        ],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="menu:order")],
    ])


def schedule_choice_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚕 Hoziroq", callback_data="schedule:now")],
        [InlineKeyboardButton(text="🗓 Vaqt belgilash", callback_data="schedule:later")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="order:cancel")],
    ])


def schedule_time_presets_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🕐 1 soatdan", callback_data="stime:60"),
            InlineKeyboardButton(text="🕑 2 soatdan", callback_data="stime:120"),
        ],
        [
            InlineKeyboardButton(text="🕕 3 soatdan", callback_data="stime:180"),
            InlineKeyboardButton(text="🌅 Ertaga 7:00", callback_data="stime:tomorrow_7"),
        ],
        [InlineKeyboardButton(text="⌨️ Aniq vaqt kiritish", callback_data="stime:custom")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="schedule:back")],
    ])


def confirm_order_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="order:confirm"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="order:cancel"),
        ],
    ])


def skip_location_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Lokatsiyasiz davom etish", callback_data="order:skip_location")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="order:cancel")],
    ])


def rating_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="1⭐", callback_data=f"rating:{order_id}:1"),
            InlineKeyboardButton(text="2⭐", callback_data=f"rating:{order_id}:2"),
            InlineKeyboardButton(text="3⭐", callback_data=f"rating:{order_id}:3"),
            InlineKeyboardButton(text="4⭐", callback_data=f"rating:{order_id}:4"),
            InlineKeyboardButton(text="5⭐", callback_data=f"rating:{order_id}:5"),
        ],
    ])


def cancel_order_user_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Buyurtmani bekor qilish", callback_data=f"order:user_cancel:{order_id}")],
    ])


# ═══════════════════════════════════════════
#  DISPATCHER
# ═══════════════════════════════════════════

def dispatcher_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Faol buyurtmalar", callback_data="disp:active_orders")],
        [
            InlineKeyboardButton(text="🚗 Haydovchilar", callback_data="disp:drivers"),
            InlineKeyboardButton(text="👥 Yo'lovchilar", callback_data="disp:users"),
        ],
        [InlineKeyboardButton(text="🔄 Yangilash", callback_data="disp:refresh")],
    ])


# ═══════════════════════════════════════════
#  MANAGER
# ═══════════════════════════════════════════

def manager_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="mgr:stats")],
        [
            InlineKeyboardButton(text="🛣 Yo'nalishlar", callback_data="mgr:routes"),
            InlineKeyboardButton(text="🚗 Haydovchilar", callback_data="mgr:drivers"),
        ],
        [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="mgr:users")],
        [InlineKeyboardButton(text="◀️ Asosiy menyu", callback_data="menu:main")],
    ])


def driver_manage_kb(driver_id: int, status: str) -> InlineKeyboardMarkup:
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
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="mgr:drivers")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def route_manage_kb(route_id: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle_text = "⏸ To'xtatish" if is_active else "▶️ Faollashtirish"
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=toggle_text, callback_data=f"mgr:route_toggle:{route_id}"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"mgr:route_delete:{route_id}"),
        ],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="mgr:routes")],
    ])


def add_route_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yangi yo'nalish", callback_data="mgr:add_route")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="mgr:menu")],
    ])


# ═══════════════════════════════════════════
#  ADMIN
# ═══════════════════════════════════════════

def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin:users")],
        [
            InlineKeyboardButton(text="👨‍💼 Manager qilish", callback_data="admin:set_manager"),
            InlineKeyboardButton(text="📋 Dispatcher qilish", callback_data="admin:set_dispatcher"),
        ],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin:stats")],
    ])


def user_role_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👨‍💼 Manager", callback_data=f"admin:role:{user_id}:manager"),
            InlineKeyboardButton(text="📋 Dispatcher", callback_data=f"admin:role:{user_id}:dispatcher"),
        ],
        [
            InlineKeyboardButton(text="👤 User", callback_data=f"admin:role:{user_id}:user"),
            InlineKeyboardButton(text="🚫 Bloklash", callback_data=f"admin:block:{user_id}"),
        ],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:users")],
    ])


# ═══════════════════════════════════════════
#  RO'YXATDAN O'TISH
# ═══════════════════════════════════════════

def registration_phone_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Keyinroq qo'shaman", callback_data="reg:skip_phone")],
    ])


# ═══════════════════════════════════════════
#  CARPOOL (JOY TO'PLASH)
# ═══════════════════════════════════════════

def trip_seats_kb() -> InlineKeyboardMarkup:
    """Haydovchi nechta joylik trip ochmoqchi."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="2️⃣ joy", callback_data="trip_seats:2"),
            InlineKeyboardButton(text="3️⃣ joy", callback_data="trip_seats:3"),
            InlineKeyboardButton(text="4️⃣ joy", callback_data="trip_seats:4"),
        ],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="menu:main")],
    ])


def trip_status_kb(trip_id: int, status: str, occupied: int, total: int) -> InlineKeyboardMarkup:
    """Haydovchi uchun trip boshqaruv paneli."""
    buttons = []

    if status == "collecting":
        if occupied >= 1:
            buttons.append([InlineKeyboardButton(
                text="🚀 Yo'lga chiqish (kutmasdan)",
                callback_data=f"ctrip:depart:{trip_id}",
            )])
        buttons.append([InlineKeyboardButton(
            text="❌ Trip bekor qilish",
            callback_data=f"ctrip:cancel:{trip_id}",
        )])
    elif status == "full":
        buttons.append([InlineKeyboardButton(
            text="🚀 Yo'lga chiqish",
            callback_data=f"ctrip:depart:{trip_id}",
        )])
    elif status == "in_progress":
        buttons.append([InlineKeyboardButton(
            text="🏁 Safarni tugatish",
            callback_data=f"ctrip:complete:{trip_id}",
        )])

    buttons.append([InlineKeyboardButton(
        text="🔄 Yangilash",
        callback_data=f"ctrip:refresh:{trip_id}",
    )])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def available_trips_kb(trips: list) -> InlineKeyboardMarkup:
    """Yo'lovchi uchun mavjud triplar ro'yxati."""
    builder = InlineKeyboardBuilder()
    for trip in trips:
        free = trip.total_seats - trip.occupied_seats
        builder.button(
            text=f"🚐 {free}/{trip.total_seats} bo'sh | {trip.price_per_seat:,} so'm",
            callback_data=f"join_trip:{trip.id}",
        )
    builder.button(text="◀️ Orqaga", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def join_trip_seats_kb(trip_id: int, max_seats: int) -> InlineKeyboardMarkup:
    """Yo'lovchi nechta joy olmoqchi."""
    buttons = []
    row = []
    for i in range(1, min(max_seats + 1, 5)):
        row.append(InlineKeyboardButton(text=f"{i}️⃣", callback_data=f"jtrip_seats:{trip_id}:{i}"))
    buttons.append(row)
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="menu:order")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def passenger_in_trip_kb(trip_id: int) -> InlineKeyboardMarkup:
    """Yo'lovchi trip da — chiqish tugmasi."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📍 Lokatsiyamni ulashish", callback_data=f"ptrip:share_loc:{trip_id}")],
        [InlineKeyboardButton(text="❌ Chiqish", callback_data=f"ptrip:leave:{trip_id}")],
    ])


def regions_kb(prefix: str = "dreg:region", cancel_cb: str = "dreg:cancel") -> InlineKeyboardMarkup:
    """Viloyatlar ro'yxati."""
    builder = InlineKeyboardBuilder()
    for region_id, region in REGIONS.items():
        builder.button(
            text=region["name"],
            callback_data=f"{prefix}:{region_id}",
        )
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data=cancel_cb))
    return builder.as_markup()


def districts_kb(region_id: str, prefix: str = "dreg:district", back_cb: str = "dreg:back_region", cancel_cb: str = "dreg:cancel") -> InlineKeyboardMarkup:
    """Tuman ro'yxati."""
    region = REGIONS.get(region_id, {})
    builder = InlineKeyboardBuilder()
    for dist_id, dist_name in region.get("districts", {}).items():
        builder.button(
            text=dist_name,
            callback_data=f"{prefix}:{region_id}:{dist_id}",
        )
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data=back_cb))
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data=cancel_cb))
    return builder.as_markup()


def driver_route_select_kb(routes: list, selected_ids: list, prefix: str = "dreg:route", done_cb: str = "dreg:done", cancel_cb: str = "dreg:cancel") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for route in routes:
        check = "✅" if route.id in selected_ids else "⬜"
        builder.button(
            text=f"{check} {route.from_name} → {route.to_name}  |  {route.price:,} so'm",
            callback_data=f"{prefix}:{route.id}",
        )
    builder.adjust(1)
    if selected_ids:
        builder.row(InlineKeyboardButton(text="✅ Tayyor", callback_data=done_cb))
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data=cancel_cb))
    return builder.as_markup()
