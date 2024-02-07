import datetime as dt

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.keyboards import (
    menu_button,
    inline_menu,
    cities_inline,
    city_shops_inline
)
from .states import ShopState, CityState, AdminState
from models.models import Shop, WorkShift, City, User, Defective, Delay
from engine import async_engine, engine


admins_id = {6215929408}
# admins_id = {}

async_session = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    future=True
)
session = sessionmaker(engine)


router = Router()
router.message.filter(F.chat.id.in_(admins_id))
router.callback_query.filter(F.message.chat.id.in_(admins_id))


def get_admins() -> None:
    """Получение списка администраторов"""
    global admins_id
    with session() as sess:
        admins = sess.query(User)\
            .filter(User.is_admin).all()
        for admin in admins:
            admins_id.add(admin.telegram_id)


@router.message(CommandStart())
async def cmd_admin_start(message: Message, state: FSMContext):
    """Старт"""

    await message.answer(
        'Админ панель',
        reply_markup=menu_button()
    )
    await state.clear()


@router.message(F.text == 'Меню')
async def admin_menu(message: Message):

    await message.answer(
        'Админ панель',
        reply_markup=inline_menu(admin=True)
    )


@router.callback_query(F.data.startswith('admin_menu'))
async def admin_page_menu(callback: CallbackQuery):
    page = int(callback.data.split('=')[1])
    await callback.message.edit_text(
        text='Админ панель',
        reply_markup=inline_menu(page=page, admin=True)
    )


@router.callback_query(F.data.startswith('admin_workshift'))
async def opened(callback: CallbackQuery):
    """Вывод открытых и закрытых смен"""
    workshift_status = {
        'open': 'открыл',
        'close': 'закрыл'
    }
    status = callback.data.split('=')[1]
    async with async_session() as sess:
        workshifts = await sess.execute(WorkShift)\
         .filter(
            WorkShift.status == status
        )\
         .filter(WorkShift.date > dt.date.today())\
         .order_by(WorkShift.date)
    if workshifts.all():
        for workshift in workshifts:
            await callback.message.answer_photo(
                caption=f'@{workshift.user.telegram_username} '
                        f'{workshift_status[status]} смену в '
                        f'{workshift.date}',
                photo=workshift.photo,
            )


@router.callback_query(F.data == 'spendings')
async def spendings(callback: CallbackQuery):
    """Траты за сутки"""
    pass


@router.callback_query(F.data == 'shop_add')
async def shop_add(callback: CallbackQuery, state: FSMContext):
    """Добавить магазин"""

    await callback.message.answer(
        text='В каком городе находится магазин?',
        reply_markup=cities_inline()
    )
    await state.set_state(ShopState.city)


@router.callback_query(F.data.startswith('city'), ShopState.city)
async def shop_city(callback: CallbackQuery, state: FSMContext):
    """Город магазина"""

    city_id = callback.data.split('=')[1]
    await state.update_data(city=city_id)
    await callback.message.answer(
        'Адрес магазина'
    )
    await state.set_state(ShopState.address)


@router.message(ShopState.address, F.text)
async def address(message: Message, state: FSMContext):
    """Адрес магазина"""

    await state.update_data(adress=message.text)
    await message.answer(
        'Уникальный ID терминала'
    )
    await state.set_state(ShopState.terminal_id)


@router.message(ShopState.terminal_id, F.text)
async def terminal_id(message: Message, state: FSMContext):
    """Получение id терминала, добавление в бд"""

    await state.update_data(terminal_id=message.text)
    shop_data = await state.get_data()
    async with async_session() as sess:
        city = await sess.execute(City).filter(City.id == shop_data['city']) \
            .first()
        shop = Shop(
            # Передать в city объект Города
            city=city,
            address=shop_data['adress'],
            terminal_id=shop_data['terminal_id']
        )
        sess.add(shop)
        sess.commit()
        await message.answer(
            'Магазин добавлен.'
        )

    await state.clear()


@router.callback_query(F.data == 'cities')
async def cities(callback: CallbackQuery):
    """ Получение информации о существующих городах """

    async with async_session() as sess:
        if not await sess.execute(City).scalar():
            await callback.message.answer(
                text='Города еще не добавлены!'
            )
        else:
            await callback.message.answer(
                text='Выберите город',
                reply_markup=cities_inline()
            )


@router.callback_query(F.data.startswith('city'))
async def city(callback: CallbackQuery):
    """ Получение информации о магазинах в городе """

    city_id = int(callback.data.split('=')[1])
    async with async_session() as sess:
        shops = await sess.execute(Shop).filter(Shop.city_id == city_id)
        if not await shops.first():
            await callback.message.answer(
                text='В городе еще нет магазина'
            )
        else:
            await callback.message.answer(
                text='Выберите магазин',
                reply_markup=city_shops_inline(city_id)
            )


@router.callback_query(F.data == 'add_city')
async def add_city(callback: CallbackQuery, state: FSMContext):
    """ Создание города """

    await callback.message.answer(
        text='Название города'
    )
    await state.set_state(CityState.name)


@router.message(CityState.name, F.text)
async def city_name(message: Message, state: FSMContext):
    """ Получение названия города """

    async with async_session() as sess:
        if await sess.execute(City).filter(City.name == message.text).first():
            await message.reply(
                'Город уже существует'
            )
        else:
            sess.add(
                City(name=message.text)
            )
            sess.commit()
            await message.answer(
                text=f'Город {message.text} добавлен!'
            )
    await state.clear()


@router.callback_query(F.data == 'defective')
async def defevtive(callback: CallbackQuery):
    """Вывод товаров с дефектом"""

    async with async_session() as sess:
        items = await sess.execute(Defective)\
            .filter(
                Defective.date > (dt.date.today() - dt.timedelta(days=14))
            ).order_by(Defective.date)
    if items.all():
        for defective in items:
            await callback.message.answer_video(
                video=defective.video,
                caption=f'@{defective.user.telegram_username}'
                f' отправил в {defective.date}'
                f' из магазина в городе {defective.shop.city.name}'
                f' по адресу: {defective.shop.address}'
            )


@router.callback_query(F.data.startswith('admin'))
async def admin(callback: CallbackQuery, state: FSMContext):
    """Редактирование администраторов"""

    status = callback.data.split('_')[1]
    await state.update_data(status=status)
    await callback.message.answer(
        text='Пришлите сообщение от аккаунта'
    )
    await state.set_state(AdminState.message)


@router.message(AdminState.message)
async def admin_action(message: Message, state: FSMContext):
    """Добавление/удаление администратора"""
    data = await state.get_data()
    async with async_session() as sess:
        user = await sess.query(User)\
            .filter(User.telegram_id == message.forward_from.id).first()
        if user:
            user.is_admin = True if data['status'] == 'add'\
                else False
            action = 'добавлен' if user.is_admin else 'удален'
            sess.add(user)
            sess.commit()
            await message.answer(
                f'Администратор {action}'
            )
        else:
            await message.answer(
                text='Пользователь еще не зарегистрирован',
            )
    get_admins()
    await state.clear()


@router.callback_query(F.data == 'delays')
async def delays(callback: CallbackQuery):
    """Опоздания"""
    async with async_session() as sess:
        delays = await sess.execute(Delay, WorkShift).join(WorkShift)\
            .filter(Delay.date > (dt.datetime.now() - dt.timedelta(days=1)))\
            .filter(WorkShift.id == Delay.workshift_id)
    if delays.all():
        for delay, workshift in delays:
            await callback.message.answer_photo(
                caption=delay.description,
                photo=workshift.photo
            )
