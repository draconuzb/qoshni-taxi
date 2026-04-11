import logging

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


def active_trip_kb(trip_id: int, trip, lang: str = "uz") -> InlineKeyboardMarkup:
    rows = []
    seat_row = []
    if trip.seats_left > 0:
        seat_row.append(InlineKeyboardButton(text=t("btn_add_seat", lang), callback_data=f"trip:phys_add:{trip_id}"))
    if trip.physical_seats > 0:
        seat_row.append(InlineKeyboardButton(text=t("btn_remove_seat", lang), callback_data=f"trip:phys_remove:{trip_id}"))
    if seat_row:
        rows.append(seat_row)
    rows.append([InlineKeyboardButton(text=t("btn_depart", lang), callback_data=f"trip:pre_depart:{trip_id}")])
    rows.append([InlineKeyboardButton(text=t("btn_cancel", lang), callback_data=f"trip:pre_abort:{trip_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def departed_trip_kb(trip_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_trip_done", lang), callback_data=f"trip:complete:{trip_id}")],
    ])


def _passengers_text(bookings: list, lang: str = "uz") -> str:
    active = [b for b in bookings if b.status == BookingStatus.ACTIVE]
    if not active:
        return t("trip_no_passengers", lang)
    lines = []
    for b in active:
        phone = b.user.phone or "—"
        line = f"  👤 {b.user.full_name} • {phone}"
        if b.comment:
            line += f"\n     💬 {b.comment}"
        lines.append(line)
    if hasattr(bookings, '__iter__'):
        # Check for physical seats from trip context (passed separately)
        pass
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  SAFAR E'LON QILISH
# ══════════════════════════════════════════════════════════════════════════════

@router.message(TextMatch("btn_announce"))
async def open_trip_text(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    if not db_user:
        await message.answer("Avval ro'yxatdan o'ting: /start")
        return

    result = await session.execute(select(Driver).where(Driver.user_id == db_user.id))
    driver = result.scalar_one_or_none()

    if not driver or driver.status != DriverStatus.VERIFIED:
        await message.answer(t("driver_not_verified", lang))
        return

    existing = await session.execute(
        select(Trip).where(Trip.driver_id == driver.id)
        .where(Trip.status.in_([TripStatus.COLLECTING, TripStatus.DEPARTED]))
    )
    if existing.scalar_one_or_none():
        await message.answer(t("driver_has_active", lang))
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
    await message.answer(
        t("trip_select_route", lang),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )
    await state.set_state(TripAnnounceState.select_route)


@router.callback_query(TripAnnounceState.select_route, F.data.startswith("trip:route:"))
async def trip_route_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str = "uz"):
    await callback.answer()
    route_id = int(callback.data.split(":")[-1])
    route = await session.get(Route, route_id)
    if not route:
        return
    await state.update_data(route_id=route.id, price=route.price)
    await callback.message.edit_text(
        f"🛣 <b>{route.from_name} ↔ {route.to_name}</b>\n\n{t('trip_select_dir', lang)}",
        reply_markup=direction_kb(route, lang),
    )
    await state.set_state(TripAnnounceState.select_direction)


@router.callback_query(TripAnnounceState.select_direction, F.data.startswith("trip:dir:"))
async def trip_direction_selected(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    await callback.answer()
    direction_str = callback.data.split(":")[-1]
    await state.update_data(direction=direction_str)
    await callback.message.edit_text(t("trip_select_seats", lang), reply_markup=seats_kb(lang))
    await state.set_state(TripAnnounceState.select_seats)


@router.callback_query(TripAnnounceState.select_seats, F.data == "trip:back_dir")
async def trip_back_to_direction(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str = "uz"):
    await callback.answer()
    data = await state.get_data()
    route = await session.get(Route, data["route_id"])
    await callback.message.edit_text(
        f"🛣 <b>{route.from_name} ↔ {route.to_name}</b>\n\n{t('trip_select_dir', lang)}",
        reply_markup=direction_kb(route, lang),
    )
    await state.set_state(TripAnnounceState.select_direction)


@router.callback_query(TripAnnounceState.select_seats, F.data.startswith("trip:seats:"))
async def trip_seats_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext, lang: str = "uz"):
    await callback.answer()
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
    )


@router.callback_query(F.data == "trip:cancel")
async def cancel_trip_announce(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(t("cancelled", lang))


# ══════════════════════════════════════════════════════════════════════════════
#  FAOL SAFAR
# ══════════════════════════════════════════════════════════════════════════════

@router.message(TextMatch("btn_active_trip"))
async def active_trip_text(message: Message, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    if not db_user:
        await message.answer("Avval ro'yxatdan o'ting: /start")
        return
    await _show_active_trip(message, session, db_user, lang)


@router.callback_query(F.data == "trip:refresh")
async def refresh_active_trip(callback: CallbackQuery, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    await callback.answer()
    if not db_user:
        await callback.answer("Avval ro'yxatdan o'ting: /start", show_alert=True)
        return
    await _show_active_trip(callback.message, session, db_user, lang, edit=True)


async def _show_active_trip(message, session: AsyncSession, db_user: User, lang: str = "uz", edit: bool = False):
    result = await session.execute(select(Driver).where(Driver.user_id == db_user.id))
    driver = result.scalar_one_or_none()
    if not driver:
        text = t("trip_no_active", lang)
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        return

    trip_result = await session.execute(
        select(Trip).where(Trip.driver_id == driver.id)
        .where(Trip.status.in_([TripStatus.COLLECTING, TripStatus.DEPARTED]))
    )
    trip = trip_result.scalar_one_or_none()

    if not trip:
        text = t("trip_no_active", lang)
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        return

    await session.refresh(trip, ["route", "bookings"])
    for b in trip.bookings:
        await session.refresh(b, ["user"])

    route = trip.route
    dir_t = _dir_text(route, TripDirection(trip.direction))
    p_text = _passengers_text(trip.bookings, lang)

    if trip.status == TripStatus.COLLECTING:
        seats_hint = t("trip_seats_left", lang, n=trip.seats_left) if trip.seats_left > 0 else t("trip_seats_full", lang)
        kb = active_trip_kb(trip.id, trip, lang)
    else:
        seats_hint = ""
        kb = departed_trip_kb(trip.id, lang)

    text = (
        f"{t('trip_active', lang)}\n\n"
        f"🛣 {dir_t}\n"
        f"💺 {trip.occupied}/{trip.total_seats} • {seats_hint}\n"
        f"💰 {trip.price_per_seat:,}\n\n"
        f"{t('trip_passengers_title', lang)}\n{p_text}"
    )

    if edit:
        await message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    else:
        await message.answer(text, reply_markup=kb, disable_web_page_preview=True)


# ══════════════════════════════════════════════════════════════════════════════
#  PHYSICAL SEATS
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("trip:phys_add:"))
async def phys_add(callback: CallbackQuery, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    if not db_user:
        await callback.answer("Avval ro'yxatdan o'ting: /start", show_alert=True)
        return
    trip_id = int(callback.data.split(":")[-1])
    trip = await session.get(Trip, trip_id)
    if not trip or trip.status != TripStatus.COLLECTING:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return
    if trip.seats_left <= 0:
        await callback.answer(t("trip_seats_full", lang), show_alert=True)
        return
    trip.physical_seats += 1
    await session.commit()
    await callback.answer(f"➕ {trip.physical_seats}")
    await _show_active_trip(callback.message, session, db_user, lang, edit=True)


@router.callback_query(F.data.startswith("trip:phys_remove:"))
async def phys_remove(callback: CallbackQuery, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    if not db_user:
        await callback.answer("Avval ro'yxatdan o'ting: /start", show_alert=True)
        return
    trip_id = int(callback.data.split(":")[-1])
    trip = await session.get(Trip, trip_id)
    if not trip or trip.physical_seats <= 0:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return
    if trip.status != TripStatus.COLLECTING:
        await callback.answer("❌ Safar faol emas.", show_alert=True)
        return
    trip.physical_seats -= 1
    await session.commit()
    await callback.answer(f"➖ {trip.physical_seats}")
    await _show_active_trip(callback.message, session, db_user, lang, edit=True)


# ══════════════════════════════════════════════════════════════════════════════
#  DEPART
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("trip:pre_depart:"))
async def pre_depart(callback: CallbackQuery, lang: str = "uz"):
    await callback.answer()
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
    await callback.answer()
    trip_id = int(callback.data.split(":")[-1])
    trip = await session.get(Trip, trip_id)
    if not trip:
        await callback.answer("❌ Safar topilmadi", show_alert=True)
        return
    if trip.status != TripStatus.COLLECTING:
        await callback.answer("❌ Safar holati mos emas", show_alert=True)
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

    for booking in active_bookings:
        blang = booking.user.language or "uz"
        try:
            await bot.send_message(
                booking.user.telegram_id,
                f"{t('trip_departed', blang)}\n\n🛣 {dir_t}\n🚗 {trip.driver.user.full_name}\n📞 {trip.driver.user.phone or '—'}",
                disable_web_page_preview=True,
            )
        except Exception:
            logging.exception("Failed to notify passenger about departure")

    p_text = _passengers_text(trip.bookings, lang)
    await callback.message.edit_text(
        f"🚀 <b>{dir_t}</b>\n\n✅ {len(active_bookings)}\n\n{t('trip_passengers_title', lang)}\n{p_text}",
        reply_markup=departed_trip_kb(trip.id, lang),
        disable_web_page_preview=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ARRIVED / COMPLETE
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("trip:pickup:"))
async def mark_passenger_picked(callback: CallbackQuery, session: AsyncSession, bot: Bot, db_user: User | None, lang: str = "uz"):
    await callback.answer()
    booking_id = int(callback.data.split(":")[-1])
    booking = await session.get(Booking, booking_id)
    if not booking:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return
    booking.status = BookingStatus.PICKED_UP
    await session.commit()
    if db_user:
        await _show_active_trip(callback.message, session, db_user, lang, edit=True)


@router.callback_query(F.data.startswith("trip:arrived:"))
async def mark_passenger_arrived(callback: CallbackQuery, session: AsyncSession, bot: Bot, db_user: User | None, lang: str = "uz"):
    await callback.answer()
    booking_id = int(callback.data.split(":")[-1])
    booking = await session.get(Booking, booking_id)
    if not booking:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return

    booking.status = BookingStatus.PICKED_UP
    await session.commit()
    await session.refresh(booking, ["user", "trip"])
    trip = booking.trip
    await session.refresh(trip, ["bookings", "driver", "route"])

    remaining = [b for b in trip.bookings if b.status == BookingStatus.ACTIVE]
    if not remaining:
        trip.status = TripStatus.COMPLETED
        trip.completed_at = datetime.utcnow()
        trip.driver.total_trips += 1
        await session.commit()

        dir_t = _dir_text(trip.route, TripDirection(trip.direction))
        await callback.message.edit_text(
            f"{t('trip_completed', lang)}\n\n🛣 {dir_t}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=t("btn_reannounce", lang),
                    callback_data=f"trip:reannounce:{trip.route_id}:{_dir_code(TripDirection(trip.direction))}:{trip.total_seats}",
                )],
            ]),
        )
        return

    if db_user:
        await _show_active_trip(callback.message, session, db_user, lang, edit=True)


@router.callback_query(F.data.startswith("trip:complete:"))
async def complete_trip(callback: CallbackQuery, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    await callback.answer()
    trip_id = int(callback.data.split(":")[-1])
    trip = await session.get(Trip, trip_id)
    if not trip:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return
    trip.status = TripStatus.COMPLETED
    trip.completed_at = datetime.utcnow()
    await session.refresh(trip, ["driver", "route"])
    trip.driver.total_trips += 1
    await session.commit()

    dir_t = _dir_text(trip.route, TripDirection(trip.direction))
    await callback.message.edit_text(
        f"{t('trip_completed', lang)}\n\n🛣 {dir_t}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=t("btn_reannounce", lang),
                callback_data=f"trip:reannounce:{trip.route_id}:{_dir_code(TripDirection(trip.direction))}:{trip.total_seats}",
            )],
        ]),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  RE-ANNOUNCE
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("trip:reannounce:"))
async def reannounce_trip(callback: CallbackQuery, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    await callback.answer()
    if not db_user:
        await callback.answer("Avval ro'yxatdan o'ting: /start", show_alert=True)
        return
    parts = callback.data.split(":")
    route_id, direction = int(parts[2]), TripDirection.A_TO_B if parts[3] == "a_to_b" else TripDirection.B_TO_A
    seats = int(parts[4])

    driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
    if not driver:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return

    # Check if driver already has an active trip
    existing = await session.execute(
        select(Trip).where(Trip.driver_id == driver.id)
        .where(Trip.status.in_([TripStatus.COLLECTING, TripStatus.DEPARTED]))
    )
    if existing.scalar_one_or_none():
        await callback.answer(t("driver_has_active", lang), show_alert=True)
        return

    route = await session.get(Route, route_id)
    if not route:
        await callback.answer("❌ Ma'lumot topilmadi", show_alert=True)
        return

    trip = Trip(
        driver_id=driver.id, route_id=route_id, direction=direction,
        total_seats=seats, booked_seats=0, price_per_seat=route.price, status=TripStatus.COLLECTING,
    )
    session.add(trip)
    await session.commit()

    await callback.message.edit_text(
        t("trip_announced", lang, route=_dir_text(route, direction), seats=seats, price=f"{route.price:,}"),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  ABORT
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("trip:pre_abort:"))
async def pre_abort(callback: CallbackQuery, lang: str = "uz"):
    await callback.answer()
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
    await callback.answer()
    trip_id = int(callback.data.split(":")[-1])
    trip = await session.get(Trip, trip_id)
    if not trip:
        await callback.answer("❌ Safar topilmadi", show_alert=True)
        return
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
            logging.exception("Failed to notify passenger about trip cancellation")

    await callback.message.edit_text(t("trip_cancelled", lang))


# ══════════════════════════════════════════════════════════════════════════════
#  STATISTIKA
# ══════════════════════════════════════════════════════════════════════════════

@router.message(TextMatch("btn_stats"))
async def driver_stats_text(message: Message, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    if not db_user:
        await message.answer("Avval ro'yxatdan o'ting: /start")
        return
    driver = (await session.execute(select(Driver).where(Driver.user_id == db_user.id))).scalar_one_or_none()
    if not driver:
        await message.answer("❌ Haydovchi ma'lumotlari topilmadi")
        return
    completed = await session.execute(
        select(Trip).where(Trip.driver_id == driver.id, Trip.status == TripStatus.COMPLETED)
    )
    total = len(completed.scalars().all())
    await message.answer(f"📊 <b>{t('btn_stats', lang)}</b>\n\n🛣 {total}\n⭐ {driver.rating:.1f}")
