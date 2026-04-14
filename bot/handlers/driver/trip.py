from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from bot.keyboards.reply_kb import driver_menu_kb
from bot.filters import TextMatch
from bot.states.user import TripAnnounceState
from core.enums import TripStatus, TripDirection, DriverStatus, BookingStatus
from core.i18n import t
from core.models import Trip, Booking, Driver
from core.models.route import Route
from core.models.user import User
from core.models.user_route import UserRoute

router = Router()

SEAT_OPTIONS = [2, 3, 4, 5, 6, 7, 8]


def _dir_text(route: Route, direction: TripDirection) -> str:
    if direction == TripDirection.A_TO_B:
        return f"{route.from_name} → {route.to_name}"
    return f"{route.to_name} → {route.from_name}"


def _dir_code(d: TripDirection) -> str:
    return "a_to_b" if d == TripDirection.A_TO_B else "b_to_a"


def _phone_link(phone: str | None) -> str:
    if not phone:
        return "—"
    clean = phone.replace(" ", "").replace("-", "")
    return f"<a href=\"tel:{clean}\">{phone}</a>"


def direction_kb(route: Route, lang: str = "uz") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"➡️ {route.from_name} → {route.to_name}", callback_data="trip:dir:a_to_b")],
        [InlineKeyboardButton(text=f"⬅️ {route.to_name} → {route.from_name}", callback_data="trip:dir:b_to_a")],
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="trip:cancel")],
    ])


def seats_kb(lang: str = "uz") -> InlineKeyboardMarkup:
    buttons = [InlineKeyboardButton(text=str(n), callback_data=f"trip:seats:{n}") for n in SEAT_OPTIONS]
    return InlineKeyboardMarkup(
        inline_keyboard=[buttons, [InlineKeyboardButton(text=t("btn_back", lang), callback_data="trip:back_dir")]],
    )


def active_trip_kb(trip_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_depart", lang), callback_data=f"trip:pre_depart:{trip_id}")],
        [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data=f"trip:pre_abort:{trip_id}")],
    ])


def _passengers_text(bookings: list, lang: str = "uz") -> str:
    active = [b for b in bookings if b.status == BookingStatus.ACTIVE]
    if not active:
        return t("trip_no_passengers", lang)
    lines = []
    for b in active:
        line = f"  👤 {b.user.full_name}\n     📞 {_phone_link(b.user.phone)}"
        if b.comment:
            line += f"\n     💬 {b.comment}"
        lines.append(line)
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  SAFAR E'LON QILISH
# ══════════════════════════════════════════════════════════════════════════════

@router.message(TextMatch("btn_announce"))
async def open_trip_text(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    if not db_user:
        return

    driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
    if not driver or driver.status != DriverStatus.VERIFIED:
        await message.answer(t("driver_not_verified", lang))
        return

    existing = (await session.execute(
        select(Trip).where(Trip.driver_id == driver.id).where(Trip.status == TripStatus.COLLECTING)
    )).scalar_one_or_none()
    if existing:
        await _show_active_trip(message, session, db_user, lang)
        return

    fav_result = await session.execute(
        select(UserRoute).where(UserRoute.user_id == db_user.id)
        .options(selectinload(UserRoute.route)).order_by(UserRoute.id)
    )
    favs = fav_result.scalars().all()

    if not favs:
        await message.answer(t("driver_no_routes", lang))
        return

    await state.update_data(driver_id=driver.id)

    if len(favs) == 1:
        route = favs[0].route
        await state.update_data(route_id=route.id, price=route.price)
        await message.answer(
            f"🛣 <b>{route.from_name} ↔ {route.to_name}</b>\n\n{t('trip_select_dir', lang)}",
            reply_markup=direction_kb(route, lang),
        )
        await state.set_state(TripAnnounceState.select_direction)
        return

    rows = []
    for fav in favs:
        r = fav.route
        name_part = f" ({r.name})" if r.name else ""
        rows.append([InlineKeyboardButton(
            text=f"🛣 {r.from_name} ↔ {r.to_name}{name_part}",
            callback_data=f"trip:route:{r.id}",
        )])
    rows.append([InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="trip:cancel")])
    await message.answer(t("trip_select_route", lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await state.set_state(TripAnnounceState.select_route)


@router.callback_query(TripAnnounceState.select_route, F.data.startswith("trip:route:"))
async def trip_route_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str = "uz"):
    route_id = int(callback.data.split(":")[-1])
    route = await session.get(Route, route_id)
    if not route: return
    await state.update_data(route_id=route.id, price=route.price)
    await callback.message.edit_text(
        f"🛣 <b>{route.from_name} ↔ {route.to_name}</b>\n\n{t('trip_select_dir', lang)}",
        reply_markup=direction_kb(route, lang),
    )
    await state.set_state(TripAnnounceState.select_direction)


@router.callback_query(TripAnnounceState.select_direction, F.data.startswith("trip:dir:"))
async def trip_direction_selected(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    await state.update_data(direction=callback.data.split(":")[-1])
    await callback.message.edit_text(t("trip_select_seats", lang), reply_markup=seats_kb(lang))
    await state.set_state(TripAnnounceState.select_seats)


@router.callback_query(TripAnnounceState.select_seats, F.data == "trip:back_dir")
async def trip_back_to_direction(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str = "uz"):
    data = await state.get_data()
    route = await session.get(Route, data["route_id"])
    await callback.message.edit_text(
        f"🛣 <b>{route.from_name} ↔ {route.to_name}</b>\n\n{t('trip_select_dir', lang)}",
        reply_markup=direction_kb(route, lang),
    )
    await state.set_state(TripAnnounceState.select_direction)


@router.callback_query(TripAnnounceState.select_seats, F.data.startswith("trip:seats:"))
async def trip_seats_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str = "uz"):
    seats = int(callback.data.split(":")[-1])
    data = await state.get_data()
    direction = TripDirection.A_TO_B if data["direction"] == "a_to_b" else TripDirection.B_TO_A
    route = await session.get(Route, data["route_id"])

    trip = Trip(
        driver_id=data["driver_id"], route_id=data["route_id"], direction=direction,
        total_seats=seats, booked_seats=0, price_per_seat=data["price"], status=TripStatus.COLLECTING,
    )
    session.add(trip)
    await session.commit()
    await state.clear()

    await callback.message.edit_text(
        t("trip_announced", lang, route=_dir_text(route, direction), seats=seats, price=f"{route.price:,}"),
        reply_markup=active_trip_kb(trip.id, lang),
    )


@router.callback_query(F.data == "trip:cancel")
async def cancel_trip_announce(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    await state.clear()
    await callback.message.edit_text(t("cancelled", lang))


# ══════════════════════════════════════════════════════════════════════════════
#  FAOL SAFAR
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "trip:refresh")
async def refresh_active_trip(callback: CallbackQuery, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    if not db_user: return
    await _show_active_trip(callback.message, session, db_user, lang, edit=True)


async def _show_active_trip(message, session: AsyncSession, db_user: User, lang: str = "uz", edit: bool = False):
    driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
    if not driver:
        text = t("trip_no_active", lang)
        if edit: await message.edit_text(text)
        else: await message.answer(text)
        return

    trip = (await session.execute(
        select(Trip).where(Trip.driver_id == driver.id).where(Trip.status == TripStatus.COLLECTING)
    )).scalar_one_or_none()

    if not trip:
        text = t("trip_no_active", lang)
        if edit: await message.edit_text(text)
        else: await message.answer(text)
        return

    await session.refresh(trip, ["route", "bookings"])
    for b in trip.bookings:
        await session.refresh(b, ["user"])

    route = trip.route
    dir_t = _dir_text(route, TripDirection(trip.direction))
    p_text = _passengers_text(trip.bookings, lang)
    seats_hint = t("trip_seats_left", lang, n=trip.seats_left) if trip.seats_left > 0 else t("trip_seats_full", lang)

    text = (
        f"{t('trip_active', lang)}\n\n"
        f"🛣 {dir_t}\n"
        f"💺 {trip.booked_seats}/{trip.total_seats} • {seats_hint}\n"
        f"💰 {trip.price_per_seat:,}\n\n"
        f"{t('trip_passengers_title', lang)}\n{p_text}"
    )

    kb = active_trip_kb(trip.id, lang)
    if edit: await message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    else: await message.answer(text, reply_markup=kb, disable_web_page_preview=True)


# ══════════════════════════════════════════════════════════════════════════════
#  YO'LGA CHIQISH (depart = trip ends)
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("trip:pre_depart:"))
async def pre_depart(callback: CallbackQuery, lang: str = "uz"):
    trip_id = int(callback.data.split(":")[-1])
    await callback.message.edit_text(
        t("confirm_depart", lang),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=t("btn_yes_depart", lang), callback_data=f"trip:depart:{trip_id}"),
                InlineKeyboardButton(text=t("btn_back", lang), callback_data="trip:refresh"),
            ],
        ]),
    )


@router.callback_query(F.data.startswith("trip:depart:"))
async def depart_trip(callback: CallbackQuery, session: AsyncSession, bot: Bot, lang: str = "uz"):
    trip_id = int(callback.data.split(":")[-1])
    trip = await session.get(Trip, trip_id)
    if not trip or trip.status != TripStatus.COLLECTING:
        return

    trip.status = TripStatus.DEPARTED
    trip.departed_at = datetime.utcnow()
    await session.commit()
    await session.refresh(trip, ["route", "bookings", "driver"])
    for b in trip.bookings:
        await session.refresh(b, ["user"])
    await session.refresh(trip.driver, ["user"])

    route = trip.route
    dir_t = _dir_text(route, TripDirection(trip.direction))
    active_bookings = [b for b in trip.bookings if b.status == BookingStatus.ACTIVE]

    # Notify all booked clients with full driver info
    for booking in active_bookings:
        blang = booking.user.language or "uz"
        try:
            await bot.send_message(
                booking.user.telegram_id,
                f"{t('trip_departed', blang)}\n\n"
                f"🛣 {dir_t}\n"
                f"👤 {trip.driver.user.full_name}\n"
                f"📞 {_phone_link(trip.driver.user.phone)}\n"
                f"🚗 {trip.driver.car_model} ({trip.driver.car_color})\n"
                f"🔢 {trip.driver.license_plate}",
                disable_web_page_preview=True,
            )
        except Exception:
            pass

    # Also increment trip count
    trip.driver.total_trips += 1
    await session.commit()

    await callback.message.edit_text(
        f"🚀 <b>{dir_t}</b>\n\n✅ {len(active_bookings)} {t('trip_passengers_title', lang)}\n\n"
        + "\n".join(f"  👤 {b.user.full_name} • {_phone_link(b.user.phone)}" for b in active_bookings),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=t("btn_reannounce", lang),
                callback_data=f"trip:reannounce:{trip.route_id}:{_dir_code(TripDirection(trip.direction))}:{trip.total_seats}",
            )],
        ]),
        disable_web_page_preview=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  RE-ANNOUNCE
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("trip:reannounce:"))
async def reannounce_trip(callback: CallbackQuery, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    if not db_user: return
    parts = callback.data.split(":")
    route_id, direction = int(parts[2]), TripDirection.A_TO_B if parts[3] == "a_to_b" else TripDirection.B_TO_A
    seats = int(parts[4])

    driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
    if not driver: return
    route = await session.get(Route, route_id)
    if not route: return

    trip = Trip(
        driver_id=driver.id, route_id=route_id, direction=direction,
        total_seats=seats, booked_seats=0, price_per_seat=route.price, status=TripStatus.COLLECTING,
    )
    session.add(trip)
    await session.commit()

    await callback.message.edit_text(
        t("trip_announced", lang, route=_dir_text(route, direction), seats=seats, price=f"{route.price:,}"),
        reply_markup=active_trip_kb(trip.id, lang),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ABORT
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("trip:pre_abort:"))
async def pre_abort(callback: CallbackQuery, lang: str = "uz"):
    trip_id = int(callback.data.split(":")[-1])
    await callback.message.edit_text(
        t("confirm_abort", lang),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=t("btn_yes_cancel", lang), callback_data=f"trip:abort:{trip_id}"),
                InlineKeyboardButton(text=t("btn_back", lang), callback_data="trip:refresh"),
            ],
        ]),
    )


@router.callback_query(F.data.startswith("trip:abort:"))
async def abort_trip(callback: CallbackQuery, session: AsyncSession, bot: Bot, lang: str = "uz"):
    trip_id = int(callback.data.split(":")[-1])
    trip = await session.get(Trip, trip_id)
    if not trip: return
    trip.status = TripStatus.CANCELLED
    await session.commit()
    await session.refresh(trip, ["route", "bookings"])
    for b in trip.bookings:
        await session.refresh(b, ["user"])
        if b.status == BookingStatus.ACTIVE:
            b.status = BookingStatus.CANCELLED
    await session.commit()

    dir_t = _dir_text(trip.route, TripDirection(trip.direction))
    for booking in trip.bookings:
        blang = booking.user.language or "uz"
        try:
            await bot.send_message(booking.user.telegram_id, f"{t('trip_cancelled', blang)}\n\n🛣 {dir_t}")
        except Exception:
            pass

    await callback.message.edit_text(t("trip_cancelled", lang))


