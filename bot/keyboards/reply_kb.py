from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from core.i18n import t


# ── Client ────────────────────────────────────────────────────────────────────

def client_menu_kb(lang: str = "uz") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("btn_taxi", lang))],
            [KeyboardButton(text=t("btn_my_routes", lang))],
            [KeyboardButton(text=t("btn_profile", lang)), KeyboardButton(text=t("btn_help", lang))],
            [KeyboardButton(text=t("btn_reload", lang))],
        ],
        resize_keyboard=True,
    )


# ── Driver ────────────────────────────────────────────────────────────────────

def driver_menu_kb(lang: str = "uz") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("btn_announce", lang))],
            [KeyboardButton(text=t("btn_my_routes", lang))],
            [KeyboardButton(text=t("btn_active_trip", lang)), KeyboardButton(text=t("btn_stats", lang))],
            [KeyboardButton(text=t("btn_reload", lang))],
            [KeyboardButton(text=t("btn_back_client", lang))],
        ],
        resize_keyboard=True,
    )


# ── Phone request ─────────────────────────────────────────────────────────────

def phone_request_kb(lang: str = "uz") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("phone_btn", lang), request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
