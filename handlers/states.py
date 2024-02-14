from aiogram.fsm.state import StatesGroup, State


class DefectiveProduct(StatesGroup):
    video = State()
    title = State()
    product_id = State()


class SpendingsState(StatesGroup):
    purchaises = State()
    money_spent = State()
    cash_receipt = State()


class Registration(StatesGroup):
    first_name = State()
    second_name = State()
    city = State()
    shop = State()


class WorkshiftState(StatesGroup):
    shift = State()
    earnings = State()
    apply = State()
    change = State()


class ShopState(StatesGroup):
    city = State()
    address = State()
    terminal_id = State()


class CityState(StatesGroup):
    name = State()


class AdminState(StatesGroup):
    message = State()


class OrderState(StatesGroup):
    product = State()
    count = State()
    create_order = State()
    name = State()
    parameters = State()
    current = State()
    select_or_create = State()  # Промежуточное состояние
