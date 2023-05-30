from aiogram.types import ReplyKeyboardMarkup, KeyboardButton,\
    InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.orm import sessionmaker

from engine import engine
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
    'Удалить администратора': 'admin_delete'
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
