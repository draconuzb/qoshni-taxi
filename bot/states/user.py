from aiogram.fsm.state import State, StatesGroup


class RegistrationState(StatesGroup):
    full_name = State()
    phone = State()
    car_model = State()
    car_color = State()
    license_plate = State()
    select_region = State()
    select_district = State()
    select_route = State()


class EditProfileState(StatesGroup):
    edit_name = State()
    edit_phone = State()
    edit_car_model = State()
    edit_car_color = State()
    edit_license_plate = State()


class FavoriteRoutesState(StatesGroup):
    select_region = State()
    select_district = State()
    select_route = State()


class TripAnnounceState(StatesGroup):
    select_route = State()
    select_direction = State()
    select_seats = State()


class BookingState(StatesGroup):
    waiting_comment = State()
    editing_comment = State()
