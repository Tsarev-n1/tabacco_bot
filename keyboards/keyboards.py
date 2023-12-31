from aiogram.types import ReplyKeyboardMarkup, KeyboardButton,\
    InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.orm import sessionmaker

from engine import engine
from sheets.actions import get_category_orders
from sheets.sheets import products
from models.models import Shop, City


worker_actions = {
    'Открыть смену': 'workshift_open',
    'Закрыть смену': 'workshift_close',
    'Брак': 'defective',
    'Траты': 'spendings',
    'Заказ': 'order',
}

admin_actions = {
    'Открытые смены': 'admin_workshift=open',
    'Закрытые смены': 'admin_workshift=close',
    'Расход за сутки': 'spendings',
    'Добавить магазин': 'shop_add',
    'Города': 'cities',
    'Добавить город': 'add_city',
    'Дефекты': 'defective',
    'Добавить администратора': 'admin_add',
    'Удалить администратора': 'admin_delete',
    'Опоздания': 'delays'
}

Session = sessionmaker(bind=engine)


def menu_button():
    kb = [
        [
            KeyboardButton(text='Меню')
        ]
    ]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    return keyboard


def inline_menu(page: int = 1, admin: bool = False):
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    size = 5
    choose_menu = 'admin' if admin else 'worker'
    actions = admin_actions if admin else worker_actions
    for i in list(actions.keys())[(page-1)*size:(page-1)*size+size]:
        builder.add(InlineKeyboardButton(
            text=i,
            callback_data=actions[i]
        ))

    if page != 1:
        builder.add(InlineKeyboardButton(
            text=page-1,
            callback_data=f'{choose_menu}_menu_page={page-1}'
        ))
        builder.adjust(1)

    if (len(actions) - (size*page)) > 0:
        builder.add(InlineKeyboardButton(
            text=page+1,
            callback_data=f'{choose_menu}_menu_page={page+1}'
        ))
        builder.adjust(1)

    builder.adjust(1)

    return builder.as_markup()


def city_shops_inline(city_id):
    """Магазины в городе"""
    builder = InlineKeyboardBuilder()
    with Session() as session:
        shops = session.query(Shop).filter(Shop.city_id == city_id)
    for shop in shops:
        builder.add(
            InlineKeyboardButton(
                text=shop.address,
                callback_data=f'shop={shop.id}'
            )
        )
    builder.adjust(2)
    return builder.as_markup()


def cities_inline():
    """Доступные города"""
    builder = InlineKeyboardBuilder()
    with Session() as sess:
        cities = sess.query(City).all()
        for city in cities:
            builder.add(InlineKeyboardButton(
                text=city.name,
                callback_data=f'city={city.id}'
            ))
    builder.adjust(1)
    return builder.as_markup()


def workshift_apply_keyboard():
    """Подтверждение запроса"""
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text='Подтвердить!',
            callback_data='earnings_apply'
        ),
        InlineKeyboardButton(
            text='Изменить',
            callback_data='earnings_change'
        )
    )
    return builder.as_markup()


def order_keyboard(products: dict = products):
    """Клавиатура для выбора категории предзаказа"""
    builder = InlineKeyboardBuilder()
    for pos, category in enumerate(products):
        builder.add(
            InlineKeyboardButton(
                text=category,
                callback_data=f'order_category={pos}'
            )
        )
    builder.adjust(1)
    return builder.as_markup()
    # Может добавить категории в модель магазина?


def order_category_keyboard(key: int, sheet_id: str):
    """Клавиатура выбора из конкретной категории"""

    orders = get_category_orders(key, sheet_id)
    builder = InlineKeyboardBuilder()
    if orders:
        for pos, order in enumerate(orders):
            builder.add(
                InlineKeyboardButton(
                    text=order,
                    callback_data=f'order_select={pos}'
                )
            )
    builder.add(
        InlineKeyboardButton(
            text='Добавить новый!',
            callback_data='order_create'
        )
    )
    return builder.as_markup()
