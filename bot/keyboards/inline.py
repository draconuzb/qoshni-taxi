from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.locations import REGIONS


# ═══════════════════════════════════════════
#  ROUTE SELECTION
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


# ═══════════════════════════════════════════
#  REGION / DISTRICT
# ═══════════════════════════════════════════

def regions_kb(prefix: str = "dreg:region", cancel_cb: str = "dreg:cancel") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for region_id, region in REGIONS.items():
        builder.button(text=region["name"], callback_data=f"{prefix}:{region_id}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data=cancel_cb))
    return builder.as_markup()


def districts_kb(region_id: str, prefix: str = "dreg:district", back_cb: str = "dreg:back_region", cancel_cb: str = "dreg:cancel") -> InlineKeyboardMarkup:
    region = REGIONS.get(region_id, {})
    builder = InlineKeyboardBuilder()
    for dist_id, dist_name in region.get("districts", {}).items():
        builder.button(text=dist_name, callback_data=f"{prefix}:{region_id}:{dist_id}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="◀️ Orqaga", callback_data=back_cb))
    builder.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data=cancel_cb))
    return builder.as_markup()


# ═══════════════════════════════════════════
#  ADMIN
# ═══════════════════════════════════════════

def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin:users")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin:stats")],
    ])


def user_role_kb(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👤 User", callback_data=f"admin:role:{user_id}:user"),
            InlineKeyboardButton(text="🚗 Driver", callback_data=f"admin:role:{user_id}:driver"),
        ],
        [InlineKeyboardButton(text="🚫 Bloklash", callback_data=f"admin:block:{user_id}")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:users")],
    ])
