from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from core.i18n import t


def client_menu_kb(lang: str = "uz") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("btn_taxi", lang))],
            [KeyboardButton(text=t("btn_settings", lang)), KeyboardButton(text=t("btn_contact", lang))],
        ],
        resize_keyboard=True,
    )


def driver_menu_kb(lang: str = "uz") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("btn_announce", lang))],
            [KeyboardButton(text=t("btn_settings", lang)), KeyboardButton(text=t("btn_contact", lang))],
        ],
        resize_keyboard=True,
    )


def phone_request_kb(lang: str = "uz") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("phone_btn", lang), request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
