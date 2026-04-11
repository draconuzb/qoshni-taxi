from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def location_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📍 Lokatsiyani yuborish", request_location=True)],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚕 Taxi chaqirish")],
            [KeyboardButton(text="📋 Buyurtmalarim"), KeyboardButton(text="⚙️ Sozlamalar")],
        ],
        resize_keyboard=True,
    )


def driver_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🟢 Online"), KeyboardButton(text="🔴 Offline")],
            [KeyboardButton(text="📋 Buyurtmalarim"), KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="⚙️ Sozlamalar")],
        ],
        resize_keyboard=True,
    )


def dispatcher_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Faol buyurtmalar")],
            [KeyboardButton(text="🚗 Haydovchilar"), KeyboardButton(text="👥 Yo'lovchilar")],
        ],
        resize_keyboard=True,
    )


def manager_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="🛣 Yo'nalishlar"), KeyboardButton(text="🚗 Haydovchilar")],
            [KeyboardButton(text="👥 Foydalanuvchilar"), KeyboardButton(text="⚙️ Sozlamalar")],
        ],
        resize_keyboard=True,
    )


def routes_inline_keyboard(routes: list, action: str = "select") -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for route in routes:
        builder.button(
            text=f"{route.from_name} → {route.to_name} ({route.price:,} so'm)",
            callback_data=f"route:{action}:{route.id}",
        )
    builder.adjust(1)
    return builder.as_markup()


def confirm_keyboard(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha", callback_data=f"{prefix}:confirm"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data=f"{prefix}:cancel"),
            ]
        ]
    )


def order_action_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"order:accept:{order_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"order:reject:{order_id}"),
            ]
        ]
    )


def passenger_count_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, 5):
        builder.button(text=str(i), callback_data=f"passengers:{i}")
    builder.adjust(4)
    return builder.as_markup()


def rating_keyboard(order_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, 6):
        builder.button(text="⭐" * i, callback_data=f"rating:{order_id}:{i}")
    builder.adjust(1)
    return builder.as_markup()
