from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.reply_kb import client_menu_kb, driver_menu_kb, phone_request_kb
from bot.keyboards.inline import regions_kb, districts_kb, routes_kb
from bot.filters import TextMatch
from bot.states.user import RegistrationState, EditProfileState, FavoriteRoutesState
from core.enums import UserRole, DriverStatus, TripStatus
from core.i18n import t, LANGS
from core.locations import REGIONS, get_region_name, get_district_name
from core.models.user import User
from core.models.driver import Driver
from core.models.route import Route
from core.models.user_route import UserRoute

from infrastructure.config import settings

router = Router()


def _get_menu_kb(user: User):
    lang = user.language or "uz"
    if user.role == UserRole.DRIVER:
        return driver_menu_kb(lang)
    return client_menu_kb(lang)


def _lang_kb() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=name, callback_data=f"lang:{code}")]
            for code, name in LANGS.items()]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _phone_link(phone: str | None) -> str:
    if not phone:
        return "—"
    clean = phone.replace(" ", "").replace("-", "")
    return f"<a href=\"tel:{clean}\">{phone}</a>"


# ══════════════════════════════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    await state.clear()

    if db_user:
        if db_user.is_blocked:
            return
        lang = db_user.language or "uz"

        # Active trip/booking hint
        status_text = ""
        if db_user.role == UserRole.DRIVER:
            drv = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
            if drv:
                from core.models import Trip
                active = (await session.execute(
                    select(Trip).where(Trip.driver_id == drv.id).where(Trip.status == TripStatus.COLLECTING)
                )).scalar_one_or_none()
                if active:
                    await session.refresh(active, ["route"])
                    status_text = f"\n\n📋 {active.route.from_name} ↔ {active.route.to_name} ({active.booked_seats}/{active.total_seats})"

        await message.answer(
            t("hello", lang, name=db_user.full_name) + status_text,
            reply_markup=_get_menu_kb(db_user),
        )
        return

    # New user → language first
    await message.answer(t("lang_select", "uz"), reply_markup=_lang_kb())


@router.callback_query(F.data.startswith("lang:"))
async def lang_selected(callback: CallbackQuery, session: AsyncSession, db_user: User | None, state: FSMContext):
    lang = callback.data.split(":")[-1]
    if lang not in LANGS:
        return

    if db_user:
        # Existing user changing language
        db_user.language = lang
        await session.commit()
        await callback.message.edit_text(t("lang_changed", lang))
        await callback.message.answer(
            t("hello", lang, name=db_user.full_name),
            reply_markup=_get_menu_kb(db_user),
        )
        return

    # New user registration
    await state.update_data(reg_lang=lang)
    await callback.message.edit_text(
        t("welcome", lang),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("role_client", lang), callback_data="reg:role:user")],
            [InlineKeyboardButton(text=t("role_driver", lang), callback_data="reg:role:driver")],
        ]),
    )


@router.callback_query(F.data.startswith("reg:role:"))
async def reg_role_selected(callback: CallbackQuery, state: FSMContext):
    role = callback.data.split(":")[-1]
    data = await state.get_data()
    lang = data.get("reg_lang", "uz")
    await state.update_data(reg_role=role)
    await callback.message.edit_text(t("enter_name", lang))
    await state.set_state(RegistrationState.full_name)


# ── Name ──────────────────────────────────────────────────────────────────────

@router.message(RegistrationState.full_name)
async def process_name(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("reg_lang", "uz")
    if not message.text or len(message.text) < 2:
        await message.answer(t("name_too_short", lang))
        return
    await state.update_data(full_name=message.text)
    await message.answer(t("thanks_name", lang, name=message.text), reply_markup=phone_request_kb(lang))
    await state.set_state(RegistrationState.phone)


# ── Phone ─────────────────────────────────────────────────────────────────────

@router.message(RegistrationState.phone, F.contact)
async def process_phone_contact(message: Message, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    lang = data.get("reg_lang", "uz")
    await state.update_data(phone=message.contact.phone_number)
    await message.answer(t("phone_accepted", lang), reply_markup=ReplyKeyboardRemove())
    await _after_phone(message, session, state, lang)


@router.message(RegistrationState.phone, F.text)
async def process_phone_text(message: Message, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    lang = data.get("reg_lang", "uz")
    phone = message.text.strip()
    if not (phone.startswith("+") and len(phone) >= 10 and phone[1:].isdigit()):
        await message.answer(t("phone_invalid", lang))
        return
    await state.update_data(phone=phone)
    await message.answer(t("phone_accepted", lang), reply_markup=ReplyKeyboardRemove())
    await _after_phone(message, session, state, lang)


async def _after_phone(message: Message, session: AsyncSession, state: FSMContext, lang: str):
    data = await state.get_data()
    if data.get("reg_role") == "driver":
        await message.answer(t("enter_car_model", lang))
        await state.set_state(RegistrationState.car_model)
    else:
        # Client — create immediately with default route
        await _create_user(message, session, state, lang)


# ── Driver car info ───────────────────────────────────────────────────────────

@router.message(RegistrationState.car_model, F.text)
async def process_car_model(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("reg_lang", "uz")
    await state.update_data(car_model=message.text.strip())
    await message.answer(t("enter_car_color", lang))
    await state.set_state(RegistrationState.car_color)


@router.message(RegistrationState.car_color, F.text)
async def process_car_color(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("reg_lang", "uz")
    await state.update_data(car_color=message.text.strip())
    await message.answer(t("enter_license_plate", lang))
    await state.set_state(RegistrationState.license_plate)


@router.message(RegistrationState.license_plate, F.text)
async def process_license_plate(message: Message, session: AsyncSession, state: FSMContext):
    data = await state.get_data()
    lang = data.get("reg_lang", "uz")
    await state.update_data(license_plate=message.text.strip().upper())
    await _create_user(message, session, state, lang)


# ── Create user (both client and driver) ──────────────────────────────────────

async def _create_user(message: Message, session: AsyncSession, state: FSMContext, lang: str):
    data = await state.get_data()
    is_driver = data.get("reg_role") == "driver"

    user = User(
        telegram_id=message.from_user.id,
        full_name=data["full_name"],
        phone=data["phone"],
        role=UserRole.DRIVER if is_driver else UserRole.USER,
        language=lang,
    )
    session.add(user)
    await session.flush()

    # Auto-assign default route
    default_route = await session.get(Route, settings.default_route_id)
    if default_route:
        session.add(UserRoute(user_id=user.id, route_id=settings.default_route_id))

    # Create driver record
    if is_driver:
        driver = Driver(
            user_id=user.id,
            car_model=data["car_model"],
            car_color=data["car_color"],
            license_plate=data["license_plate"],
            status=DriverStatus.VERIFIED,
        )
        session.add(driver)

    await session.commit()
    await state.clear()

    route_text = f"{default_route.from_name} ↔ {default_route.to_name}" if default_route else "—"

    if is_driver:
        await message.answer(
            t("driver_reg_success", lang, car=data["car_model"], color=data["car_color"],
              plate=data["license_plate"], route=route_text),
        )
        await message.answer(t("driver_menu", lang), reply_markup=driver_menu_kb(lang))
    else:
        await message.answer(
            t("reg_success", lang, name=data["full_name"], phone=data["phone"], route=route_text),
        )
        await message.answer(t("main_menu", lang), reply_markup=client_menu_kb(lang))


@router.callback_query(F.data == "reg:cancel")
async def reg_cancel(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    lang = data.get("reg_lang", "uz")
    await state.clear()
    await callback.message.edit_text(t("cancelled", lang))


# ══════════════════════════════════════════════════════════════════════════════
#  SOZLAMALAR (settings menu)
# ══════════════════════════════════════════════════════════════════════════════

def _settings_kb(lang: str, is_driver: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=t("btn_my_routes", lang), callback_data="settings:routes")],
        [InlineKeyboardButton(text=t("btn_profile", lang), callback_data="settings:profile")],
        [InlineKeyboardButton(text=t("btn_contact", lang), callback_data="settings:contact")],
        [InlineKeyboardButton(text=t("btn_help", lang), callback_data="settings:help")],
        [InlineKeyboardButton(text=t("btn_change_lang", lang), callback_data="profile:change_lang")],
    ]
    if is_driver:
        rows.append([InlineKeyboardButton(text=t("btn_back_client", lang), callback_data="settings:switch_client")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(TextMatch("btn_settings"))
async def show_settings(message: Message, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    if not db_user:
        await message.answer(t("register_first", lang))
        return
    await message.answer(
        t("settings_title", lang),
        reply_markup=_settings_kb(lang, db_user.role == UserRole.DRIVER),
    )


@router.callback_query(F.data == "settings:routes")
async def settings_routes(callback: CallbackQuery, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    if not db_user: return
    await callback.answer()
    await _show_favorites(callback.message, session, db_user, lang)


@router.callback_query(F.data == "settings:profile")
async def settings_profile(callback: CallbackQuery, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    if not db_user: return
    await callback.answer()
    text = await _build_profile_text(db_user, session, lang)
    await callback.message.answer(text, reply_markup=_profile_kb(lang, db_user.role == UserRole.DRIVER), disable_web_page_preview=True)


@router.callback_query(F.data == "settings:help")
async def settings_help(callback: CallbackQuery, lang: str = "uz"):
    await callback.answer()
    await callback.message.answer(t("help_text", lang))


@router.message(TextMatch("btn_contact"))
async def contact_text(message: Message, lang: str = "uz"):
    phone = settings.contact_phone
    clean = phone.replace(" ", "").replace("-", "")
    await message.answer(
        t("contact_text", lang, phone=f"<a href=\"tel:{clean}\">{phone}</a>"),
        disable_web_page_preview=True,
    )


@router.callback_query(F.data == "settings:contact")
async def settings_contact(callback: CallbackQuery, lang: str = "uz"):
    await callback.answer()
    phone = settings.contact_phone
    clean = phone.replace(" ", "").replace("-", "")
    await callback.message.answer(
        t("contact_text", lang, phone=f"<a href=\"tel:{clean}\">{phone}</a>"),
        disable_web_page_preview=True,
    )


@router.callback_query(F.data == "settings:switch_client")
async def settings_switch_client(callback: CallbackQuery, db_user: User | None, lang: str = "uz"):
    if not db_user: return
    await callback.answer()
    await callback.message.answer(t("client_mode", lang, name=db_user.full_name), reply_markup=client_menu_kb(lang))


@router.callback_query(F.data == "settings:active_trip")
async def settings_active_trip(callback: CallbackQuery, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    if not db_user: return
    await callback.answer()
    # Import here to avoid circular
    from bot.handlers.driver.trip import _show_active_trip
    await _show_active_trip(callback.message, session, db_user, lang)


@router.callback_query(F.data == "settings:stats")
async def settings_stats(callback: CallbackQuery, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    if not db_user: return
    await callback.answer()
    driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
    if not driver:
        await callback.message.answer("—")
        return
    await callback.message.answer(f"📊 <b>{t('btn_stats', lang)}</b>\n\n🛣 {driver.total_trips}")


# ══════════════════════════════════════════════════════════════════════════════
#  MENING YO'NALISHLARIM
# ══════════════════════════════════════════════════════════════════════════════


async def _show_favorites(message: Message, session: AsyncSession, db_user: User, lang: str, edit: bool = False):
    result = await session.execute(
        select(UserRoute).where(UserRoute.user_id == db_user.id)
        .options(selectinload(UserRoute.route)).order_by(UserRoute.id)
    )
    favs = result.scalars().all()

    text = t("my_routes_title", lang) + "\n\n"
    if not favs:
        text += t("no_fav_routes", lang)
    else:
        for i, fav in enumerate(favs, 1):
            r = fav.route
            name_part = f" ({r.name})" if r.name else ""
            text += f"{i}. {r.from_name} ↔ {r.to_name}{name_part}\n"

    rows = []
    for fav in favs:
        r = fav.route
        rows.append([InlineKeyboardButton(text=f"❌ {r.from_name} ↔ {r.to_name}", callback_data=f"fav:remove:{fav.id}")])
    rows.append([InlineKeyboardButton(text=t("btn_add_route", lang), callback_data="fav:add")])

    if edit:
        await message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    else:
        await message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


# ── Add favorite ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "fav:add")
async def fav_add_start(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    await callback.message.edit_text(
        t("select_region", lang),
        reply_markup=regions_kb(prefix="fav:region", cancel_cb="fav:cancel"),
    )
    await state.set_state(FavoriteRoutesState.select_region)


@router.callback_query(FavoriteRoutesState.select_region, F.data.startswith("fav:region:"))
async def fav_region_selected(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    region_id = callback.data.split(":", 2)[2]
    if region_id not in REGIONS:
        return
    await state.update_data(fav_region=region_id)
    await callback.message.edit_text(
        f"📍 {get_region_name(region_id)}\n\n{t('select_district', lang)}",
        reply_markup=districts_kb(region_id, prefix="fav:district", back_cb="fav:back_region", cancel_cb="fav:cancel"),
    )
    await state.set_state(FavoriteRoutesState.select_district)


@router.callback_query(F.data == "fav:back_region")
async def fav_back_region(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    await callback.message.edit_text(
        t("select_region", lang),
        reply_markup=regions_kb(prefix="fav:region", cancel_cb="fav:cancel"),
    )
    await state.set_state(FavoriteRoutesState.select_region)


@router.callback_query(FavoriteRoutesState.select_district, F.data.startswith("fav:district:"))
async def fav_district_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str = "uz"):
    parts = callback.data.split(":", 3)
    region_id, district_id = parts[2], parts[3]

    result = await session.execute(select(Route).where(Route.is_active == True).order_by(Route.id))
    all_routes = result.scalars().all()
    relevant = [r for r in all_routes if r.district == district_id]
    if not relevant:
        relevant = list(all_routes)
    if not relevant:
        await callback.message.edit_text(t("no_routes", lang),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=t("btn_back", lang), callback_data="fav:back_region")]
            ]))
        return

    await callback.message.edit_text(
        f"📍 <b>{get_district_name(region_id, district_id)}, {get_region_name(region_id)}</b>\n\n{t('select_route', lang)}",
        reply_markup=routes_kb(relevant, prefix="fav:route"),
    )
    await state.set_state(FavoriteRoutesState.select_route)


@router.callback_query(FavoriteRoutesState.select_route, F.data.startswith("fav:route:"))
async def fav_route_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext, db_user: User | None, lang: str = "uz"):
    if not db_user:
        return
    route_id = int(callback.data.split(":")[-1])
    existing = await session.execute(select(UserRoute).where(UserRoute.user_id == db_user.id, UserRoute.route_id == route_id))
    if existing.scalar_one_or_none():
        await callback.answer(t("route_exists", lang), show_alert=True)
        return
    session.add(UserRoute(user_id=db_user.id, route_id=route_id))
    await session.commit()
    await state.clear()
    await callback.answer(t("route_added", lang))
    await _show_favorites(callback.message, session, db_user, lang, edit=True)


@router.callback_query(F.data == "fav:cancel")
async def fav_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    await state.clear()
    if db_user:
        await _show_favorites(callback.message, session, db_user, lang, edit=True)


@router.callback_query(F.data.startswith("fav:remove:"))
async def fav_remove(callback: CallbackQuery, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    if not db_user:
        return
    fav_id = int(callback.data.split(":")[-1])
    fav = await session.get(UserRoute, fav_id)
    if not fav or fav.user_id != db_user.id:
        return
    await session.delete(fav)
    await session.commit()
    await callback.answer(t("route_removed", lang))
    await _show_favorites(callback.message, session, db_user, lang, edit=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PROFILE
# ══════════════════════════════════════════════════════════════════════════════

def _profile_kb(lang: str, is_driver: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=t("btn_edit_name", lang), callback_data="profile:edit_name"),
            InlineKeyboardButton(text=t("btn_edit_phone", lang), callback_data="profile:edit_phone"),
        ],
    ]
    if is_driver:
        rows.append([
            InlineKeyboardButton(text=t("btn_edit_car", lang), callback_data="profile:edit_car"),
            InlineKeyboardButton(text=t("btn_edit_color", lang), callback_data="profile:edit_color"),
            InlineKeyboardButton(text=t("btn_edit_plate", lang), callback_data="profile:edit_plate"),
        ])
    rows.append([InlineKeyboardButton(text=t("btn_change_lang", lang), callback_data="profile:change_lang")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _build_profile_text(db_user: User, session: AsyncSession, lang: str) -> str:
    role_text = t("role_driver_label", lang) if db_user.role == UserRole.DRIVER else t("role_passenger", lang)

    result = await session.execute(
        select(UserRoute).where(UserRoute.user_id == db_user.id).options(selectinload(UserRoute.route))
    )
    favs = result.scalars().all()
    routes_text = ""
    if favs:
        routes_text = f"\n🛣 {t('btn_my_routes', lang)}:"
        for fav in favs:
            routes_text += f"\n   • {fav.route.from_name} ↔ {fav.route.to_name}"

    text = (
        f"{t('profile_title', lang)}\n\n"
        f"📝 {db_user.full_name}\n"
        f"📞 {_phone_link(db_user.phone)}\n"
        f"🏷 {role_text}\n"
        f"🌐 {LANGS.get(db_user.language, 'Ozbek')}"
        f"{routes_text}\n"
        f"📅 {db_user.created_at.strftime('%d.%m.%Y')}"
    )

    if db_user.role == UserRole.DRIVER:
        driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
        if driver:
            text += f"\n\n🚗 {driver.car_model} ({driver.car_color})\n🔢 {driver.license_plate}"

    return text


@router.callback_query(F.data == "profile:change_lang")
async def profile_change_lang(callback: CallbackQuery, lang: str = "uz"):
    await callback.message.edit_text(t("lang_select", lang), reply_markup=_lang_kb())


# ── Edit handlers ─────────────────────────────────────────────────────────────

@router.callback_query(F.data == "profile:edit_name")
async def start_edit_name(callback: CallbackQuery, state: FSMContext, db_user: User | None, lang: str = "uz"):
    if not db_user: return
    await callback.message.answer(t("edit_name_prompt", lang, val=db_user.full_name))
    await state.set_state(EditProfileState.edit_name)
    await callback.answer()

@router.message(EditProfileState.edit_name)
async def process_edit_name(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    if not db_user or not message.text or len(message.text) < 2:
        await message.answer(t("name_too_short", lang))
        return
    db_user.full_name = message.text
    await session.commit()
    await state.clear()
    await message.answer(t("name_changed", lang, name=message.text), reply_markup=_get_menu_kb(db_user))

@router.callback_query(F.data == "profile:edit_phone")
async def start_edit_phone(callback: CallbackQuery, state: FSMContext, db_user: User | None, lang: str = "uz"):
    if not db_user: return
    await callback.message.answer(t("edit_phone_prompt", lang, val=db_user.phone or "—"), reply_markup=phone_request_kb(lang))
    await state.set_state(EditProfileState.edit_phone)
    await callback.answer()

@router.message(EditProfileState.edit_phone, F.contact)
async def process_edit_phone_contact(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    if not db_user: return
    db_user.phone = message.contact.phone_number
    await session.commit()
    await state.clear()
    await message.answer(t("phone_changed", lang, phone=db_user.phone), reply_markup=_get_menu_kb(db_user))

@router.message(EditProfileState.edit_phone, F.text)
async def process_edit_phone_text(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    if not db_user: return
    phone = message.text.strip()
    if not (phone.startswith("+") and len(phone) >= 10 and phone[1:].isdigit()):
        await message.answer(t("phone_invalid", lang))
        return
    db_user.phone = phone
    await session.commit()
    await state.clear()
    await message.answer(t("phone_changed", lang, phone=phone), reply_markup=_get_menu_kb(db_user))

@router.callback_query(F.data == "profile:edit_car")
async def start_edit_car(callback: CallbackQuery, session: AsyncSession, state: FSMContext, db_user: User | None, lang: str = "uz"):
    if not db_user: return
    driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
    if not driver: return
    await callback.message.answer(t("edit_car_prompt", lang, val=driver.car_model))
    await state.set_state(EditProfileState.edit_car_model)
    await callback.answer()

@router.message(EditProfileState.edit_car_model, F.text)
async def process_edit_car(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    if not db_user: return
    driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
    if driver: driver.car_model = message.text.strip(); await session.commit()
    await state.clear()
    await message.answer(t("car_changed", lang, val=message.text.strip()), reply_markup=_get_menu_kb(db_user))

@router.callback_query(F.data == "profile:edit_color")
async def start_edit_color(callback: CallbackQuery, session: AsyncSession, state: FSMContext, db_user: User | None, lang: str = "uz"):
    if not db_user: return
    driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
    if not driver: return
    await callback.message.answer(t("edit_color_prompt", lang, val=driver.car_color))
    await state.set_state(EditProfileState.edit_car_color)
    await callback.answer()

@router.message(EditProfileState.edit_car_color, F.text)
async def process_edit_color(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    if not db_user: return
    driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
    if driver: driver.car_color = message.text.strip(); await session.commit()
    await state.clear()
    await message.answer(t("car_changed", lang, val=message.text.strip()), reply_markup=_get_menu_kb(db_user))

@router.callback_query(F.data == "profile:edit_plate")
async def start_edit_plate(callback: CallbackQuery, session: AsyncSession, state: FSMContext, db_user: User | None, lang: str = "uz"):
    if not db_user: return
    driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
    if not driver: return
    await callback.message.answer(t("edit_plate_prompt", lang, val=driver.license_plate))
    await state.set_state(EditProfileState.edit_license_plate)
    await callback.answer()

@router.message(EditProfileState.edit_license_plate, F.text)
async def process_edit_plate(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    if not db_user: return
    driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
    if driver: driver.license_plate = message.text.strip().upper(); await session.commit()
    await state.clear()
    await message.answer(t("car_changed", lang, val=message.text.strip().upper()), reply_markup=_get_menu_kb(db_user))


