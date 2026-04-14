import logging

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.reply_kb import client_menu_kb
from bot.filters import TextMatch
from bot.states.user import BookingState
from core.enums import TripStatus, TripDirection, BookingStatus
from core.i18n import t
from core.models import Trip, Booking, Driver, Route
from core.models.user import User
from core.models.user_route import UserRoute

router = Router()


def _phone_link(phone: str | None) -> str:
    if not phone:
        return "—"
    clean = phone.replace(" ", "").replace("-", "")
    return f"<a href=\"tel:{clean}\">{phone}</a>"


def _dir_code(d: TripDirection) -> str:
    return "a_to_b" if d == TripDirection.A_TO_B else "b_to_a"


def _dir_text(route: Route, direction: TripDirection) -> str:
    if direction == TripDirection.A_TO_B:
        return f"{route.from_name} → {route.to_name}"
    return f"{route.to_name} → {route.from_name}"


# ══════════════════════════════════════════════════════════════════════════════
#  TAXI CHAQIRISH
# ══════════════════════════════════════════════════════════════════════════════

@router.message(TextMatch("btn_taxi"))
async def taxi_call(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    if not db_user:
        await message.answer(t("register_first", lang))
        return
    await state.clear()

    # Check active booking
    existing = await session.execute(
        select(Booking).join(Trip)
        .where(Booking.user_id == db_user.id, Booking.status == BookingStatus.ACTIVE)
        .where(Trip.status.in_([TripStatus.COLLECTING, TripStatus.DEPARTED]))
    )
    active_booking = existing.scalar_one_or_none()
    if active_booking:
        await _show_active_booking(message, session, active_booking, lang)
        return

    # Load favorites
    result = await session.execute(
        select(UserRoute).where(UserRoute.user_id == db_user.id)
        .options(selectinload(UserRoute.route)).order_by(UserRoute.id)
    )
    favs = result.scalars().all()

    if not favs:
        await message.answer(t("taxi_no_routes", lang))
        return

    # One route with remembered direction → one-tap
    if len(favs) == 1 and favs[0].last_direction:
        route = favs[0].route
        direction = TripDirection(favs[0].last_direction)
        await _show_trips(message, session, route, direction, lang)
        return

    # One route, no direction → ask
    if len(favs) == 1:
        route = favs[0].route
        await message.answer(
            f"🛣 <b>{route.from_name} ↔ {route.to_name}</b>\n\n{t('taxi_select_dir', lang)}",
            reply_markup=_direction_kb(route.id, route),
        )
        return

    # Multiple routes
    rows = []
    for fav in favs:
        r = fav.route
        name_part = f" ({r.name})" if r.name else ""
        if fav.last_direction:
            d = TripDirection(fav.last_direction)
            rows.append([InlineKeyboardButton(
                text=f"🚕 {_dir_text(r, d)}{name_part}",
                callback_data=f"taxi:quick:{r.id}:{_dir_code(d)}",
            )])
        else:
            rows.append([InlineKeyboardButton(
                text=f"🛣 {r.from_name} ↔ {r.to_name}{name_part}",
                callback_data=f"taxi:route:{r.id}",
            )])

    await message.answer(t("taxi_select_route", lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


# ── Direction ─────────────────────────────────────────────────────────────────

def _direction_kb(route_id: int, route: Route) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"➡️ {route.from_name} → {route.to_name}", callback_data=f"taxi:dir:{route_id}:a_to_b")],
        [InlineKeyboardButton(text=f"⬅️ {route.to_name} → {route.from_name}", callback_data=f"taxi:dir:{route_id}:b_to_a")],
    ])


@router.callback_query(F.data.startswith("taxi:route:"))
async def taxi_route_selected(callback: CallbackQuery, session: AsyncSession, lang: str = "uz"):
    await callback.answer()
    route_id = int(callback.data.split(":")[-1])
    route = await session.get(Route, route_id)
    if not route:
        return
    await callback.message.edit_text(
        f"🛣 <b>{route.from_name} ↔ {route.to_name}</b>\n\n{t('taxi_select_dir', lang)}",
        reply_markup=_direction_kb(route_id, route),
    )


@router.callback_query(F.data.startswith("taxi:quick:"))
async def taxi_quick(callback: CallbackQuery, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    await callback.answer()
    if not db_user:
        return
    parts = callback.data.split(":")
    route_id = int(parts[2])
    direction = TripDirection.A_TO_B if parts[3] == "a_to_b" else TripDirection.B_TO_A
    route = await session.get(Route, route_id)
    if not route:
        return
    await _show_trips(callback.message, session, route, direction, lang, edit=True)


@router.callback_query(F.data.startswith("taxi:dir:"))
async def taxi_direction_selected(callback: CallbackQuery, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    await callback.answer()
    if not db_user:
        return
    parts = callback.data.split(":")
    route_id = int(parts[2])
    direction = TripDirection.A_TO_B if parts[3] == "a_to_b" else TripDirection.B_TO_A
    route = await session.get(Route, route_id)
    if not route:
        return

    # Remember direction
    fav = (await session.execute(
        select(UserRoute).where(UserRoute.user_id == db_user.id, UserRoute.route_id == route_id)
    )).scalar_one_or_none()
    if fav:
        fav.last_direction = _dir_code(direction)
        await session.commit()

    await _show_trips(callback.message, session, route, direction, lang, edit=True)


# ── Show trips ────────────────────────────────────────────────────────────────

async def _show_trips(message, session: AsyncSession, route: Route, direction: TripDirection, lang: str = "uz", edit: bool = False):
    result = await session.execute(
        select(Trip)
        .where(Trip.route_id == route.id, Trip.direction == direction, Trip.status == TripStatus.COLLECTING)
        .options(selectinload(Trip.driver).selectinload(Driver.user))
        .order_by(Trip.created_at.desc())
    )
    trips = result.scalars().all()
    dir_t = _dir_text(route, direction)
    refresh_cb = f"taxi:dir:{route.id}:{_dir_code(direction)}"

    if not trips:
        text = f"🛣 <b>{dir_t}</b>\n\n{t('taxi_no_drivers', lang)}"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_refresh", lang), callback_data=refresh_cb)],
            [InlineKeyboardButton(text=t("btn_change_dir", lang), callback_data=f"taxi:route:{route.id}")],
        ])
    else:
        text = f"🛣 <b>{dir_t}</b>\n\n"
        rows = []
        for trip in trips:
            d = trip.driver
            u = d.user if d else None
            hint = " 🔥" if trip.seats_left <= 2 else ""
            text += (
                f"🚗 <b>{u.full_name if u else '—'}</b>\n"
                f"   🚙 {d.car_model} ({d.car_color}) • {d.license_plate}\n"
                f"   📞 {_phone_link(u.phone if u else None)}\n"
                f"   💺 {trip.seats_left}/{trip.total_seats}{hint} • 💰 {trip.price_per_seat:,}\n\n"
            )
            rows.append([InlineKeyboardButton(
                text=f"✅ {u.full_name if u else '—'} • {trip.seats_left} • {trip.price_per_seat:,}",
                callback_data=f"book:start:{trip.id}",
            )])
        rows.append([InlineKeyboardButton(text=t("btn_refresh", lang), callback_data=refresh_cb)])
        kb = InlineKeyboardMarkup(inline_keyboard=rows)

    if edit:
        await message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    else:
        await message.answer(text, reply_markup=kb, disable_web_page_preview=True)


# ══════════════════════════════════════════════════════════════════════════════
#  BOOKING
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("book:start:"))
async def book_start(callback: CallbackQuery, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    if not db_user:
        return
    trip_id = int(callback.data.split(":")[-1])
    trip = await session.get(Trip, trip_id)
    if not trip or trip.status != TripStatus.COLLECTING:
        await callback.answer(t("trip_cancelled", lang), show_alert=True)
        return
    if trip.is_full:
        await callback.answer(t("trip_seats_full", lang), show_alert=True)
        return

    existing = await session.execute(
        select(Booking).where(Booking.trip_id == trip_id, Booking.user_id == db_user.id, Booking.status == BookingStatus.ACTIVE)
    )
    if existing.scalar_one_or_none():
        await callback.answer(t("route_exists", lang), show_alert=True)
        return

    await state.update_data(booking_trip_id=trip_id)
    await callback.message.edit_text(t("book_comment_ask", lang))
    await state.set_state(BookingState.waiting_comment)
    await callback.answer()


@router.message(BookingState.waiting_comment, F.text == "/skip")
async def book_skip_comment(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, bot: Bot, lang: str = "uz"):
    if not db_user:
        return
    await _create_booking(message, session, db_user, state, bot, lang, comment=None)


@router.message(BookingState.waiting_comment, F.text == "/cancel")
async def book_cancel_comment(message: Message, state: FSMContext, lang: str = "uz"):
    await state.clear()
    await message.answer(t("cancelled", lang), reply_markup=client_menu_kb(lang))


@router.message(BookingState.waiting_comment, F.text)
async def book_with_comment(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, bot: Bot, lang: str = "uz"):
    if not db_user:
        return
    await _create_booking(message, session, db_user, state, bot, lang, comment=message.text.strip()[:500])


@router.message(BookingState.waiting_comment)
async def book_comment_invalid(message: Message, state: FSMContext, lang: str = "uz"):
    await message.answer(
        "📝 /skip\n/cancel",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t("btn_cancel", lang), callback_data="book:fsm_cancel")],
        ]),
    )


@router.callback_query(F.data == "book:fsm_cancel")
async def book_fsm_cancel(callback: CallbackQuery, state: FSMContext, lang: str = "uz"):
    await state.clear()
    await callback.message.edit_text(t("cancelled", lang))
    await callback.answer()


async def _create_booking(message: Message, session: AsyncSession, db_user: User, state: FSMContext, bot: Bot, lang: str, comment: str | None):
    data = await state.get_data()
    trip_id = data.get("booking_trip_id")
    await state.clear()

    if not trip_id:
        await message.answer(t("cancelled", lang), reply_markup=client_menu_kb(lang))
        return

    trip = await session.execute(
        select(Trip).where(Trip.id == trip_id).with_for_update()
    )
    trip = trip.scalar_one_or_none()
    if not trip or trip.status != TripStatus.COLLECTING or trip.is_full:
        await message.answer(t("trip_cancelled", lang), reply_markup=client_menu_kb(lang))
        return

    booking = Booking(trip_id=trip_id, user_id=db_user.id, comment=comment, status=BookingStatus.ACTIVE)
    session.add(booking)
    trip.booked_seats += 1
    await session.commit()
    await session.refresh(trip, ["driver", "route"])
    await session.refresh(trip.driver, ["user"])

    route = trip.route
    dir_t = _dir_text(route, TripDirection(trip.direction))
    comment_text = f"\n💬 {comment}" if comment else ""
    seats_hint = f"\n\n{t('book_seats_full', lang)}" if trip.is_full else f"\n\n{t('book_seats_left', lang, n=trip.seats_left)}"

    await message.answer(
        f"{t('book_success', lang)}\n\n"
        f"🛣 {dir_t}\n"
        f"🚗 {trip.driver.user.full_name}\n"
        f"🚙 {trip.driver.car_model} ({trip.driver.car_color}) • {trip.driver.license_plate}\n"
        f"📞 {_phone_link(trip.driver.user.phone)}\n"
        f"💰 {trip.price_per_seat:,}"
        f"{comment_text}{seats_hint}",
        reply_markup=_booking_kb(booking.id, lang),
        disable_web_page_preview=True,
    )

    # Notify driver in driver's language
    dlang = trip.driver.user.language or "uz"
    driver_comment = f"\n💬 {comment}" if comment else ""
    seats_info = t("trip_seats_full", dlang) if trip.is_full else t("trip_seats_left", dlang, n=trip.seats_left)
    try:
        await bot.send_message(
            trip.driver.user.telegram_id,
            f"{t('new_booking_driver', dlang)}\n\n"
            f"👤 {db_user.full_name}\n"
            f"📞 {_phone_link(db_user.phone)}\n"
            f"👥 {trip.booked_seats}/{trip.total_seats}\n"
            f"{seats_info}{driver_comment}",
            disable_web_page_preview=True,
        )
    except Exception:
        logging.exception("Failed to notify driver about new booking")


def _booking_kb(booking_id: int, lang: str = "uz") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=t("btn_edit_comment", lang), callback_data=f"book:edit_comment:{booking_id}"),
            InlineKeyboardButton(text=t("btn_del_comment", lang), callback_data=f"book:del_comment:{booking_id}"),
        ],
        [InlineKeyboardButton(text=t("btn_cancel_booking", lang), callback_data=f"book:pre_cancel:{booking_id}")],
    ])


# ══════════════════════════════════════════════════════════════════════════════
#  COMMENT EDIT / DELETE
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("book:edit_comment:"))
async def edit_comment_start(callback: CallbackQuery, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    if not db_user:
        return
    booking_id = int(callback.data.split(":")[-1])
    booking = await session.get(Booking, booking_id)
    if not booking or booking.user_id != db_user.id:
        return
    if booking.status != BookingStatus.ACTIVE:
        await callback.answer("❌ Bu bron faol emas.", show_alert=True)
        return
    current = booking.comment or "—"
    await state.update_data(edit_booking_id=booking_id)
    await callback.message.answer(t("edit_name_prompt", lang, val=current))
    await state.set_state(BookingState.editing_comment)
    await callback.answer()


@router.message(BookingState.editing_comment, F.text)
async def edit_comment_save(message: Message, session: AsyncSession, db_user: User | None, state: FSMContext, lang: str = "uz"):
    if not db_user:
        return
    data = await state.get_data()
    booking_id = data.get("edit_booking_id")
    await state.clear()
    if not booking_id:
        return
    booking = await session.get(Booking, booking_id)
    if not booking or booking.user_id != db_user.id:
        return
    booking.comment = message.text.strip()[:500]
    await session.commit()
    await message.answer(f"✅ 💬 <b>{booking.comment}</b>", reply_markup=client_menu_kb(lang))


@router.message(BookingState.editing_comment)
async def edit_comment_invalid(message: Message, state: FSMContext):
    await message.answer("📝 Iltimos, matn yuboring.")


@router.callback_query(F.data.startswith("book:del_comment:"))
async def delete_comment(callback: CallbackQuery, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    if not db_user:
        return
    booking_id = int(callback.data.split(":")[-1])
    booking = await session.get(Booking, booking_id)
    if not booking or booking.user_id != db_user.id:
        return
    if booking.status != BookingStatus.ACTIVE:
        await callback.answer("❌ Bu bron faol emas.", show_alert=True)
        return
    booking.comment = None
    await session.commit()
    await callback.answer(t("route_removed", lang))


# ══════════════════════════════════════════════════════════════════════════════
#  CANCEL BOOKING
# ══════════════════════════════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("book:pre_cancel:"))
async def pre_cancel_booking(callback: CallbackQuery, lang: str = "uz"):
    await callback.answer()
    booking_id = int(callback.data.split(":")[-1])
    await callback.message.edit_text(
        t("confirm_cancel", lang),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=t("btn_yes_cancel", lang), callback_data=f"book:cancel:{booking_id}"),
                InlineKeyboardButton(text=t("btn_no", lang), callback_data=f"book:keep:{booking_id}"),
            ],
        ]),
    )


@router.callback_query(F.data.startswith("book:keep:"))
async def keep_booking(callback: CallbackQuery, session: AsyncSession, db_user: User | None, lang: str = "uz"):
    await callback.answer()
    if not db_user:
        return
    booking_id = int(callback.data.split(":")[-1])
    booking = await session.get(Booking, booking_id)
    if booking:
        await _show_active_booking_edit(callback.message, session, booking, lang)


@router.callback_query(F.data.startswith("book:cancel:"))
async def cancel_booking(callback: CallbackQuery, session: AsyncSession, db_user: User | None, bot: Bot, lang: str = "uz"):
    await callback.answer()
    if not db_user:
        return
    booking_id = int(callback.data.split(":")[-1])
    booking = await session.get(Booking, booking_id)
    if not booking or booking.user_id != db_user.id:
        await callback.message.edit_text("❌ Bron topilmadi.")
        return
    if booking.status != BookingStatus.ACTIVE:
        await callback.message.edit_text("ℹ️ Bu bron allaqachon bekor qilingan.")
        return

    await session.refresh(booking, ["trip"])
    trip = booking.trip
    if trip.status == TripStatus.DEPARTED:
        await callback.message.edit_text("🚗 Transport yo'lda — endi bekor qilib bo'lmaydi.")
        return

    booking.status = BookingStatus.CANCELLED
    trip.booked_seats = max(0, trip.booked_seats - 1)
    await session.commit()
    await session.refresh(trip, ["driver"])
    await session.refresh(trip.driver, ["user"])

    await callback.message.edit_text(t("booking_cancelled", lang))

    dlang = trip.driver.user.language or "uz"
    try:
        await bot.send_message(
            trip.driver.user.telegram_id,
            f"❌ {db_user.full_name}\n👥 {trip.booked_seats}/{trip.total_seats}",
        )
    except Exception:
        logging.exception("Failed to notify driver about booking cancellation")


# ══════════════════════════════════════════════════════════════════════════════
#  ACTIVE BOOKING DISPLAY
# ══════════════════════════════════════════════════════════════════════════════

async def _show_active_booking(message: Message, session: AsyncSession, booking: Booking, lang: str = "uz"):
    await session.refresh(booking, ["trip"])
    trip = booking.trip
    await session.refresh(trip, ["route", "driver"])
    await session.refresh(trip.driver, ["user"])
    route = trip.route

    dir_t = _dir_text(route, TripDirection(trip.direction))
    comment_text = f"\n💬 {booking.comment}" if booking.comment else ""
    seats_hint = f"\n{t('book_seats_left', lang, n=trip.seats_left)}" if trip.status == TripStatus.COLLECTING and trip.seats_left > 0 else ""

    await message.answer(
        f"📋 {t('book_success', lang)}\n\n"
        f"🛣 {dir_t}\n"
        f"🚗 {trip.driver.user.full_name}\n"
        f"🚙 {trip.driver.car_model} ({trip.driver.car_color}) • {trip.driver.license_plate}\n"
        f"📞 {_phone_link(trip.driver.user.phone)}\n"
        f"💰 {trip.price_per_seat:,}"
        f"{comment_text}{seats_hint}",
        reply_markup=_booking_kb(booking.id, lang),
        disable_web_page_preview=True,
    )


async def _show_active_booking_edit(message: Message, session: AsyncSession, booking: Booking, lang: str = "uz"):
    await session.refresh(booking, ["trip"])
    trip = booking.trip
    await session.refresh(trip, ["route", "driver"])
    await session.refresh(trip.driver, ["user"])
    route = trip.route

    dir_t = _dir_text(route, TripDirection(trip.direction))
    comment_text = f"\n💬 {booking.comment}" if booking.comment else ""

    await message.edit_text(
        f"📋 {t('book_success', lang)}\n\n"
        f"🛣 {dir_t}\n"
        f"🚗 {trip.driver.user.full_name}\n"
        f"🚙 {trip.driver.car_model} ({trip.driver.car_color}) • {trip.driver.license_plate}\n"
        f"📞 {_phone_link(trip.driver.user.phone)}\n"
        f"💰 {trip.price_per_seat:,}"
        f"{comment_text}",
        reply_markup=_booking_kb(booking.id, lang),
        disable_web_page_preview=True,
    )
