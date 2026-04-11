from aiogram.fsm.state import State, StatesGroup


class RouteCreateState(StatesGroup):
    from_name = State()
    to_name = State()
    price = State()


class RoutePriceEditState(StatesGroup):
    new_price = State()


class UserSearchState(StatesGroup):
    query = State()
