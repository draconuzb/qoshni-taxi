from aiogram import Router, F
from aiogram.filters import CommandStart, Command
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
from core.enums import UserRole, DriverStatus
from core.i18n import t, LANGS
from core.locations import REGIONS, get_region_name, get_district_name
from core.models.user import User
from core.models.driver import Driver
from core.models.route import Route
from core.models.user_route import UserRoute

router = Router()


# ══════════════════════════════════════════════════════════════════════════════
#  /cancel — global, catches in any FSM state
# ══════════════════════════════════════════════════════════════════════════════

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.")


def _get_menu_kb(user: User):
    lang = user.language or "uz"
    if user.role == UserRole.DRIVER:
        return driver_menu_kb(lang)
    return client_menu_kb(lang)


def _lang_kb() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=name, callback_data=f"lang:{code}")]
            for code, name in LANGS.items()]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ══════════════════════════════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    await state.clear()

    if db_user:
        if db_user.is_blocked:
            await message.answer("⛔ Siz bloklangansiz.")
            return
        lang = db_user.language or "uz"

        # Active trip/booking hint
        status_text = ""
        if db_user.role == UserRole.DRIVER:
            drv = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
            if drv:
                from core.models import Trip
                active = (await session.execute(
                    select(Trip).where(Trip.driver_id == drv.id).where(Trip.status.in_(["collecting", "departed"]))
                )).scalar_one_or_none()
                if active:
                    await session.refresh(active, ["route"])
                    status_text = f"\n\n📋 {active.route.from_name} ↔ {active.route.to_name} ({active.occupied}/{active.total_seats})"
        else:
            from core.models import Trip, Booking
            from core.enums import BookingStatus, TripStatus
            active = (await session.execute(
                select(Booking).join(Trip)
                .where(Booking.user_id == db_user.id, Booking.status == BookingStatus.ACTIVE)
                .where(Trip.status.in_([TripStatus.COLLECTING, TripStatus.DEPARTED]))
            )).scalar_one_or_none()
            if active:
                await session.refresh(active, ["trip"])
                await session.refresh(active.trip, ["route"])
                status_text = f"\n\n📋 {active.trip.route.from_name} ↔ {active.trip.route.to_name}"

        await message.answer(
            t("hello", lang, name=db_user.full_name) + status_text,
            reply_markup=_get_menu_kb(db_user),
        )
        return

    # New user → language first
    await message.answer(
        t("lang_select", "uz"),
        reply_markup=_lang_kb(),
    )


@router.callback_query(F.data.startswith("lang:"))
async def lang_selected(callback: CallbackQuery, session: AsyncSession, db_user: User | None, state: FSMContext):
    await callback.answer()
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

    # New user registration → save lang in state, ask role
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
    await callback.answer()
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
    if len(message.text) > 100:
        await message.answer("📝 Ism juda uzun (max 100 belgi).")
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
        await message.answer(t("select_first_route", lang),
            reply_markup=regions_kb(prefix="reg:region", cancel_cb="reg:cancel"),
        )
        await state.set_state(RegistrationState.select_region)


# ── Driver car info (registration) ───────────────────────────────────────────

@router.message(RegistrationState.car_model, F.text)
async def process_car_model(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("reg_lang", "uz")
    if len(message.text.strip()) > 100:
        await message.answer("📝 Juda uzun (max 100 belgi).")
        return
    await state.update_data(car_model=message.text.strip())
    await message.answer(t("enter_car_color", lang))
    await state.set_state(RegistrationState.car_color)


@router.message(RegistrationState.car_model)
async def process_car_model_invalid(message: Message, state: FSMContext):
    await message.answer("📝 Iltimos, matn yuboring.")


@router.message(RegistrationState.car_color, F.text)
async def process_car_color(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("reg_lang", "uz")
    if len(message.text.strip()) > 50:
        await message.answer("📝 Juda uzun (max 50 belgi).")
        return
    await state.update_data(car_color=message.text.strip())
    await message.answer(t("enter_license_plate", lang))
    await state.set_state(RegistrationState.license_plate)


@router.message(RegistrationState.car_color)
async def process_car_color_invalid(message: Message, state: FSMContext):
    await message.answer("📝 Iltimos, matn yuboring.")


@router.message(RegistrationState.license_plate, F.text)
async def process_license_plate(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get("reg_lang", "uz")
    if len(message.text.strip()) > 20:
        await message.answer("📝 Juda uzun (max 20 belgi).")
        return
    await state.update_data(license_plate=message.text.strip().upper())
    await message.answer(t("select_first_route", lang),
        reply_markup=regions_kb(prefix="reg:region", cancel_cb="reg:cancel"),
    )
    await state.set_state(RegistrationState.select_region)


@router.message(RegistrationState.license_plate)
async def process_license_plate_invalid(message: Message, state: FSMContext):
    await message.answer("📝 Iltimos, matn yuboring.")


# ── Region/District/Route selection (registration) ───────────────────────────

@router.callback_query(RegistrationState.select_region, F.data.startswith("reg:region:"))
async def reg_region_selected(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    region_id = callback.data.split(":", 2)[2]
    if region_id not in REGIONS:
        return
    data = await state.get_data()
    lang = data.get("reg_lang", "uz")
    await state.update_data(reg_region=region_id)
    await callback.message.edit_text(
        f"📍 {get_region_name(region_id)}\n\n{t('select_district', lang)}",
        reply_markup=districts_kb(region_id, prefix="reg:district", back_cb="reg:back_region", cancel_cb="reg:cancel"),
    )
    await state.set_state(RegistrationState.select_district)


@router.callback_query(F.data == "reg:back_region")
async def reg_back_region(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    lang = data.get("reg_lang", "uz")
    await callback.message.edit_text(
        t("select_region", lang),
        reply_markup=regions_kb(prefix="reg:region", cancel_cb="reg:cancel"),
    )
    await state.set_state(RegistrationState.select_region)


@router.callback_query(RegistrationState.select_district, F.data.startswith("reg:district:"))
async def reg_district_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await callback.answer()
    parts = callback.data.split(":", 3)
    region_id, district_id = parts[2], parts[3]
    data = await state.get_data()
    lang = data.get("reg_lang", "uz")
    await state.update_data(reg_region=region_id, reg_district=district_id)

    result = await session.execute(select(Route).where(Route.is_active == True).order_by(Route.id))
    all_routes = result.scalars().all()
    relevant = [r for r in all_routes if r.district == district_id or r.from_district == district_id or r.to_district == district_id]
    if not relevant:
        relevant = list(all_routes)
    if not relevant:
        await callback.message.edit_text(t("no_routes", lang),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=t("btn_back", lang), callback_data="reg:back_region")]
            ]))
        return

    await callback.message.edit_text(
        f"📍 <b>{get_district_name(region_id, district_id)}, {get_region_name(region_id)}</b>\n\n{t('select_route', lang)}",
        reply_markup=routes_kb(relevant, prefix="reg:route"),
    )
    await state.set_state(RegistrationState.select_route)


@router.callback_query(RegistrationState.select_route, F.data.startswith("reg:route:"))
async def reg_route_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    await callback.answer()
    route_id = int(callback.data.split(":")[-1])
    route = await session.get(Route, route_id)
    if not route:
        return
    data = await state.get_data()
    lang = data.get("reg_lang", "uz")
    is_driver = data.get("reg_role") == "driver"

    # Create user
    user = User(
        telegram_id=callback.from_user.id,
        full_name=data["full_name"],
        phone=data["phone"],
        role=UserRole.DRIVER if is_driver else UserRole.USER,
        language=lang,
    )
    session.add(user)
    await session.flush()

    # Add favorite route
    session.add(UserRoute(user_id=user.id, route_id=route_id))

    # Create driver record if driver
    if is_driver:
        from core.models import Driver
        driver = Driver(
            user_id=user.id,
            car_model=data["car_model"],
            car_color=data["car_color"],
            license_plate=data["license_plate"],
            route_id=route_id,
            status=DriverStatus.PENDING_VERIFICATION,
        )
        session.add(driver)

    await session.commit()
    await state.clear()

    if is_driver:
        await callback.message.edit_text(
            t("driver_reg_success", lang, car=data["car_model"], color=data["car_color"],
              plate=data["license_plate"], route=f"{route.from_name} ↔ {route.to_name}"),
        )
        await callback.message.answer(t("driver_menu", lang), reply_markup=driver_menu_kb(lang))
    else:
        await callback.message.edit_text(
            t("reg_success", lang, name=data["full_name"], phone=data["phone"], route=f"{route.from_name} ↔ {route.to_name}"),
        )
        await callback.message.answer(t("main_menu", lang), reply_markup=client_menu_kb(lang))


@router.callback_query(F.data == "reg:cancel")
async def reg_cancel(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    lang = data.get("reg_lang", "uz")
    await state.clear()
    await callback.message.edit_text(t("cancelled", lang))


# ══════════════════════════════════════════════════════════════════════════════
#  MENING YO'NALISHLARIM
# ══════════════════════════════════════════════════════════════════════════════

@router.message(TextMatch("btn_my_routes"))
async def show_my_routes(message: Message, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    if not db_user:
        await message.answer(t("register_first", lang))
        return
    await _show_favorites(message, session, db_user, lang)


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


@router.callback_query(F.data == "fav:add")
async def fav_add_start(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    await callback.answer()
    await callback.message.edit_text(
        t("select_region", lang),
        reply_markup=regions_kb(prefix="fav:region", cancel_cb="fav:cancel"),
    )
    await state.set_state(FavoriteRoutesState.select_region)


@router.callback_query(FavoriteRoutesState.select_region, F.data.startswith("fav:region:"))
async def fav_region_selected(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    await callback.answer()
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
    await callback.answer()
    await callback.message.edit_text(
        t("select_region", lang),
        reply_markup=regions_kb(prefix="fav:region", cancel_cb="fav:cancel"),
    )
    await state.set_state(FavoriteRoutesState.select_region)


@router.callback_query(FavoriteRoutesState.select_district, F.data.startswith("fav:district:"))
async def fav_district_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str = "uz"):
    await callback.answer()
    parts = callback.data.split(":", 3)
    region_id, district_id = parts[2], parts[3]

    result = await session.execute(select(Route).where(Route.is_active == True).order_by(Route.id))
    all_routes = result.scalars().all()
    relevant = [r for r in all_routes if r.district == district_id or r.from_district == district_id or r.to_district == district_id]
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
        await callback.answer("Avval ro'yxatdan o'ting: /start", show_alert=True)
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
    await callback.answer()
    await state.clear()
    if db_user:
        await _show_favorites(callback.message, session, db_user, lang, edit=True)


@router.callback_query(F.data.startswith("fav:remove:"))
async def fav_remove(callback: CallbackQuery, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    if not db_user:
        await callback.answer("Avval ro'yxatdan o'ting: /start", show_alert=True)
        return
    fav_id = int(callback.data.split(":")[-1])
    fav = await session.get(UserRoute, fav_id)
    if not fav or fav.user_id != db_user.id:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return
    await session.delete(fav)
    await session.commit()
    await callback.answer(t("route_removed", lang))
    await _show_favorites(callback.message, session, db_user, lang, edit=True)


# ══════════════════════════════════════════════════════════════════════════════
#  SWITCH TO CLIENT
# ══════════════════════════════════════════════════════════════════════════════

@router.message(TextMatch("btn_back_client"))
async def switch_to_client(message: Message, db_user: User | None, lang: str = "uz"):
    if not db_user:
        await message.answer("Avval ro'yxatdan o'ting: /start")
        return
    await message.answer(t("client_mode", lang, name=db_user.full_name), reply_markup=client_menu_kb(lang))


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


@router.message(TextMatch("btn_profile"))
async def show_profile(message: Message, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    if not db_user:
        await message.answer(t("register_first", lang))
        return
    text = await _build_profile_text(db_user, session, lang)
    await message.answer(text, reply_markup=_profile_kb(lang, db_user.role == UserRole.DRIVER))


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
        f"📞 {db_user.phone or '—'}\n"
        f"🏷 {role_text}\n"
        f"🌐 {LANGS.get(db_user.language, 'Ozbek')}"
        f"{routes_text}\n"
        f"📅 {db_user.created_at.strftime('%d.%m.%Y')}"
    )

    if db_user.role == UserRole.DRIVER:
        driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
        if driver:
            text += f"\n\n🚗 {driver.car_model} ({driver.car_color})\n🔢 {driver.license_plate}\n⭐ {driver.rating:.1f}"

    return text


# ── Language change from profile ──────────────────────────────────────────────

@router.callback_query(F.data == "profile:change_lang")
async def profile_change_lang(callback: CallbackQuery, lang: str = "uz"):
    await callback.answer()
    await callback.message.edit_text(t("lang_select", lang), reply_markup=_lang_kb())


# ── Edit name ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "profile:edit_name")
async def start_edit_name(callback: CallbackQuery, state: FSMContext, db_user: User | None, lang: str = "uz"):
    if not db_user:
        await callback.answer("Avval ro'yxatdan o'ting: /start", show_alert=True)
        return
    await callback.message.answer(t("edit_name_prompt", lang, val=db_user.full_name))
    await state.set_state(EditProfileState.edit_name)
    await callback.answer()


@router.message(EditProfileState.edit_name, F.text)
async def process_edit_name(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    if not db_user or len(message.text) < 2:
        await message.answer(t("name_too_short", lang))
        return
    db_user.full_name = message.text
    await session.commit()
    await state.clear()
    await message.answer(t("name_changed", lang, name=message.text), reply_markup=_get_menu_kb(db_user))


@router.message(EditProfileState.edit_name)
async def process_edit_name_invalid(message: Message, state: FSMContext):
    await message.answer("📝 Iltimos, matn yuboring.")


# ── Edit phone ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "profile:edit_phone")
async def start_edit_phone(callback: CallbackQuery, state: FSMContext, db_user: User | None, lang: str = "uz"):
    if not db_user:
        await callback.answer("Avval ro'yxatdan o'ting: /start", show_alert=True)
        return
    await callback.message.answer(t("edit_phone_prompt", lang, val=db_user.phone or "—"), reply_markup=phone_request_kb(lang))
    await state.set_state(EditProfileState.edit_phone)
    await callback.answer()


@router.message(EditProfileState.edit_phone, F.contact)
async def process_edit_phone_contact(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    if not db_user:
        await message.answer("Avval ro'yxatdan o'ting: /start")
        return
    db_user.phone = message.contact.phone_number
    await session.commit()
    await state.clear()
    await message.answer(t("phone_changed", lang, phone=db_user.phone), reply_markup=_get_menu_kb(db_user))


@router.message(EditProfileState.edit_phone, F.text)
async def process_edit_phone_text(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    if not db_user:
        await message.answer("Avval ro'yxatdan o'ting: /start")
        return
    phone = message.text.strip()
    if not (phone.startswith("+") and len(phone) >= 10 and phone[1:].isdigit()):
        await message.answer(t("phone_invalid", lang))
        return
    db_user.phone = phone
    await session.commit()
    await state.clear()
    await message.answer(t("phone_changed", lang, phone=phone), reply_markup=_get_menu_kb(db_user))


# ── Edit car ──────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "profile:edit_car")
async def start_edit_car(callback: CallbackQuery, session: AsyncSession, state: FSMContext, db_user: User | None, lang: str = "uz"):
    if not db_user:
        await callback.answer("Avval ro'yxatdan o'ting: /start", show_alert=True)
        return
    driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
    if not driver:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return
    await callback.message.answer(t("edit_car_prompt", lang, val=driver.car_model))
    await state.set_state(EditProfileState.edit_car_model)
    await callback.answer()


@router.message(EditProfileState.edit_car_model, F.text)
async def process_edit_car(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    if not db_user:
        await message.answer("Avval ro'yxatdan o'ting: /start")
        return
    driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
    if driver:
        driver.car_model = message.text.strip()
        await session.commit()
    await state.clear()
    await message.answer(t("car_changed", lang, val=message.text.strip()), reply_markup=_get_menu_kb(db_user))


@router.message(EditProfileState.edit_car_model)
async def process_edit_car_invalid(message: Message, state: FSMContext):
    await message.answer("📝 Iltimos, matn yuboring.")


@router.callback_query(F.data == "profile:edit_color")
async def start_edit_color(callback: CallbackQuery, session: AsyncSession, state: FSMContext, db_user: User | None, lang: str = "uz"):
    if not db_user:
        await callback.answer("Avval ro'yxatdan o'ting: /start", show_alert=True)
        return
    driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
    if not driver:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return
    await callback.message.answer(t("edit_color_prompt", lang, val=driver.car_color))
    await state.set_state(EditProfileState.edit_car_color)
    await callback.answer()


@router.message(EditProfileState.edit_car_color, F.text)
async def process_edit_color(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    if not db_user:
        await message.answer("Avval ro'yxatdan o'ting: /start")
        return
    driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
    if driver:
        driver.car_color = message.text.strip()
        await session.commit()
    await state.clear()
    await message.answer(t("car_changed", lang, val=message.text.strip()), reply_markup=_get_menu_kb(db_user))


@router.message(EditProfileState.edit_car_color)
async def process_edit_color_invalid(message: Message, state: FSMContext):
    await message.answer("📝 Iltimos, matn yuboring.")


@router.callback_query(F.data == "profile:edit_plate")
async def start_edit_plate(callback: CallbackQuery, session: AsyncSession, state: FSMContext, db_user: User | None, lang: str = "uz"):
    if not db_user:
        await callback.answer("Avval ro'yxatdan o'ting: /start", show_alert=True)
        return
    driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
    if not driver:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return
    await callback.message.answer(t("edit_plate_prompt", lang, val=driver.license_plate))
    await state.set_state(EditProfileState.edit_license_plate)
    await callback.answer()


@router.message(EditProfileState.edit_license_plate, F.text)
async def process_edit_plate(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    if not db_user:
        await message.answer("Avval ro'yxatdan o'ting: /start")
        return
    driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
    if driver:
        driver.license_plate = message.text.strip().upper()
        await session.commit()
    await state.clear()
    await message.answer(t("car_changed", lang, val=message.text.strip().upper()), reply_markup=_get_menu_kb(db_user))


@router.message(EditProfileState.edit_license_plate)
async def process_edit_plate_invalid(message: Message, state: FSMContext):
    await message.answer("📝 Iltimos, matn yuboring.")


# ══════════════════════════════════════════════════════════════════════════════
#  MENU HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

@router.message(TextMatch("btn_reload"))
async def restart_menu(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    await state.clear()
    if not db_user:
        await message.answer(t("register_first", lang))
        return
    await message.answer(t("menu_refreshed", lang), reply_markup=_get_menu_kb(db_user))


@router.message(TextMatch("btn_help"))
async def show_help(message: Message, lang: str = "uz"):
    await message.answer(t("help_text", lang))
