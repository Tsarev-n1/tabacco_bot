import datetime as dt

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.ext.asyncio import AsyncSession


from keyboards.keyboards import (
    menu_button,
    inline_menu,
    workshift_apply_keyboard,
    order_keyboard,
    order_category_keyboard
)
from .states import (DefectiveProduct, SpendingsState,
                     WorkshiftState, OrderState)
from .anonymous import workers_id
from models.models import User, WorkShift, Defective, Spending, Delay, \
    Shop
from engine import async_engine
from sheets.actions import (
    workshift_open, preorder_create,
    preorder_update
)
from sheets.sheets import products
from bot import bot


router = Router()
router.message.filter(F.chat.id.in_(workers_id))
router.callback_query.filter(F.message.chat.id.in_(workers_id))

async_session = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    future=True
)


@router.message(CommandStart())
async def cmd_worker_start(message: Message, state: FSMContext):
    """Старт"""

    await message.answer(
        f'Привет, {message.chat.first_name}',
        reply_markup=menu_button()
    )
    await state.clear()


@router.message(F.text == 'Меню')
async def worker_menu(message: Message):
    await message.answer(
        'Панель для работников 🎲',
        reply_markup=inline_menu()
    )


@router.callback_query(F.data.startswith('worker_menu'))
async def menu(callback: CallbackQuery):
    """Инлайн меню"""
    page = int(callback.data.split('=')[1])

    await callback.message.edit_text(
        text='Панель для работников 🎲',
        reply_markup=inline_menu(page)
    )


@router.callback_query(F.data.startswith('workshift'))
async def open(callback: CallbackQuery, state: FSMContext):
    """Открытие/Закрытие смены"""
    await callback.message.answer(
        'Пришлите фото'
    )
    direction = callback.data.split('_')[1]
    await state.set_data(status=direction)
    await state.set_state(WorkshiftState.shift)


@router.message(F.photo, WorkshiftState.shift)
async def open_photo(message: Message, state: FSMContext):
    """Получение фото смены"""
    data = await state.get_data()
    status = True if data['status'] == 'open' else False
    reply_status = 'открыта' if status else 'закрыта'
    photo = message.photo[-1].file_id
    async with async_session() as sess:
        user = await sess.execute(User) \
            .filter(User.telegram_id == message.chat.id) \
            .first()
        workshift = WorkShift(
                user=user,
                photo=photo,
                status='open' if status else 'close',
                shop_id=user.shop_id
            )
        shop = await sess.execute(Shop) \
            .filter(Shop.id == user.shop_id).first()
        sess.add(workshift)
        sess.commit()
        if status and message.date.time() > dt.time(hour=10):
            delay = Delay(
                user=user,
                shop=user.shop,
                workshift_id=workshift.id,
                description=f'@{user.telegram_username} открыл смену в '
                f'{message.date.time()}'
            )
            sess.add(delay)
            sess.commit()
    await message.reply(
        f'Смена {reply_status} \n'
        f'{message.date.time()} \n'
        f'{message.date.date()}'
    )
    if status:
        workshift_open(user, shop.wokrsheet, status)
        await state.clear()
    else:
        await message.reply(
            'Выручка?'
        )
        await state.update_data(user=user, sheet_id=shop.wokrsheet)
        await state.set_state(WorkshiftState.earnings)


@router.message(WorkshiftState.earnings, F.regexp(r'\d+'))
async def workshift_earnings(state: FSMContext, message: Message):
    """Получение прибыли при закрытии смены"""

    # При желании добавить в опоздания раннее закрытие
    earnings = int(message.text)
    await state.update_data(earnings=earnings)

    await message.reply(
        f'Смена закрыта!\n'
        f'Выручка составила {earnings}\n'
        f'Все верно?',
        reply_markup=workshift_apply_keyboard()
    )
    await state.set_state(WorkshiftState.change)


@router.callback_query(F.data.startswith('earnings'), WorkshiftState.change)
async def workshift_apply(state: FSMContext, callback: CallbackQuery):
    """Прием/Изменение прибыли"""
    status = callback.data.split('_')[1]
    data = await state.get_data()
    user = data.get('user')
    sheet_id = data.get('sheet_id')
    if status == 'apply':
        earnings = data.get('earnings')
        workshift_open(
            user=user, sheet_id=sheet_id,
            open=False, money=earnings
        )
        await state.clear()
    else:
        await callback.answer(
            'Введите новую сумму!'
        )
        await state.set_state(WorkshiftState.earnings)


@router.callback_query(F.data == 'defective')
async def cmd_defective(callback: CallbackQuery, state: FSMContext):
    """Бракованный товар"""

    await callback.message.answer(
        'Пришлите видео с товаром'
    )
    await state.set_state(DefectiveProduct.video)


@router.message(DefectiveProduct.video, F.video)
async def video(message: Message, state: FSMContext):
    """Получение видео с браком"""

    await state.update_data(video=message.video.file_id)
    await message.answer(
        'Наименование товара'
    )
    await state.set_state(DefectiveProduct.title)


@router.message(DefectiveProduct.title)
async def title(message: Message, state: FSMContext):
    """Получить название бракованного товара"""

    await state.update_data(name=message.text)
    await message.answer(
        'Артикул'
    )
    await state.set_state(DefectiveProduct.product_id)


@router.message(
    DefectiveProduct.product_id,
    F.text.func(lambda text: int(text) > 0)
)
async def product_id(message: Message, state: FSMContext):
    """Получить артикул бракованного товара"""

    await state.update_data(article=int(message.text))
    data = await state.get_data()
    async with async_session() as sess:
        user = await sess.execute(User) \
            .filter(User.telegram_id == message.chat.id)\
            .first()
        defective_item = Defective(
            name=data['name'],
            article_number=data['article'],
            user=user,
            shop_id=user.shop_id,
            video=data['video']
        )
        sess.add(defective_item)
        sess.commit()
    await message.answer(
        'Запрос принят'
    )
    await state.clear()


@router.callback_query(F.data == 'spendings')
async def spendings(callback: CallbackQuery, state: FSMContext):
    """Траты"""

    await callback.message.answer(
        'На что потрачено?'
    )
    await state.set_state(SpendingsState.purchaises)


@router.message(SpendingsState.purchaises, F.text)
async def purchaises(message: Message, state: FSMContext):
    """Получение списка трат"""

    await state.update_data(description=message.text)
    await message.answer(
        'Сколько потрачено рублей'
    )
    await state.set_state(SpendingsState.money_spent)


@router.message(
    SpendingsState.money_spent,
    F.text.func(lambda text: int(text) > 0)
)
async def money_spent(message: Message, state: FSMContext):
    """Получение количества потраченных денег"""

    await state.update_data(money=int(message.text))
    await message.answer(
        'Пришлите фото чека'
    )
    await state.set_state(SpendingsState.cash_receipt)


@router.message(SpendingsState.cash_receipt, F.photo)
async def cash_receipt(message: Message, state: FSMContext):
    """Получение фото чека"""

    photo = message.photo[-1].file_id
    await state.update_data(photo=photo)
    data = await state.get_data()
    async with async_session() as sess:
        user = await sess.execute(User)\
            .filter(User.telegram_id == message.chat.id)\
            .first()
        spent = Spending(
            description=data['description'],
            photo=data['photo'],
            money_spent=data['money'],
            user=user,
            shop=user.shop
        )
        sess.add(spent)
        sess.commit()
    await message.answer(
        'Запрос принят'
    )
    await state.clear()


@router.callback_query(F.data == 'order')
async def order(callback: CallbackQuery, state: FSMContext):
    """Запрос на заказ товара"""
    await callback.message.answer(
        'Что необходимо заказать?',
        reply_markup=order_keyboard()
    )
    await state.set_state(OrderState.product)


@router.callback_query(
    F.data.startswith('order_category'),
    OrderState.product
)
async def order_current(callback: CallbackQuery, state: FSMContext):
    """Выбор товара из категории"""
    key = int(callback.data.split('=')[1])
    async with async_session() as sess:
        user = await sess.execute(User) \
            .filter(User.telegram_id == callback.from_user.id) \
            .options(joinedload(User.shop)).first()
        shop = user.shop
    await bot.edit_message_text(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        text='Выберите продукт',
        reply_markup=order_category_keyboard(key, shop.worksheet)
    )
    await state.update_data(
        category_pos=key,
        worksheet=shop.worksheet,
        parameters_set={})
    await state.set_state(OrderState.select_or_create)


@router.callback_query(
    F.data.startswith('order_select'),
    OrderState.select_or_create
)
async def order_select(callback: CallbackQuery, state: FSMContext):
    """Обработка выбранного предзаказа"""

    order_pos = int(callback.data.split('=')[1])
    await bot.edit_message_text(
        text='Выберите количество',
        chat_id=callback.message.from_user.id,
        message_id=callback.message.message_id
    )
    await state.update_data(order_pos=order_pos)
    await state.set_state(OrderState.count)


@router.callback_query(F.data == 'order_create', OrderState.select_or_create)
async def order_create(callback: CallbackQuery, state: FSMContext):
    """Добавление нового заказа"""
    await bot.edit_message_text(
        chat_id=callback.from_user.id,
        message_id=callback.message.message_id,
        text='Название продукта.'
    )
    await state.set_state(OrderState.name)


@router.message(OrderState.name, F.text)
async def order_name(message: Message, state: FSMContext):
    """Создание заказа"""

    #  Получение параметров, либо переход к количеству
    data = await state.get_data()
    parameters = list(products.values())[data['category_pos']][0]

    new_state = OrderState.parameters if parameters else OrderState.count
    answer = parameters[0] if parameters else 'Выберите количество'

    await state.update_data(
        parameters=parameters,
        name=message.text,
        create=True  # Значение о том, что заказ создавался
    )
    await message.answer(
        answer
    )
    await state.set_state(new_state)


@router.message(F.text, OrderState.parameters)
async def order_parameters(message: Message, state: FSMContext):
    """Установка параметров заказа"""

    data = await state.get_data()
    parameters = data['parameters']
    parameter = parameters.pop(0)
    new_parameter = {parameter: message.text}
    await state.update_data({
        'parameters_set': data['parameters_set'].update(new_parameter)
    })
    if parameters:
        await message.answer(
            parameters[0]
        )
        await state.update_data(parameters=parameters)
    else:
        await message.answer(
            'Выберите количество'
        )
        await state.set_state(OrderState.count)


@router.message(F.text.func(lambda text: int(text) > 0), OrderState.count)
async def order_count(message: Message, state: FSMContext):
    """Количество товара"""
    data = await state.get_data()

    # Проверяем созданный заказ или уже имеющийся
    create = data.get('create')
    if create:
        # Создаем предзаказ
        preorder_create(
            category_pos=data['category_pos'],
            preorder_name=data['name'],
            sheet_id=data['worksheet'],
            count=int(message.text),
            parameters=data['parameters_set']
        )
        message = 'Заказ создан'
    else:
        preorder_update(
            sheet_id=data['worksheet'],
            category_pos=data['category_pos'],
            count=data['count'],
            order_pos=data['order_pos']
            )
        message = 'Заказ обновлен'
    #  TODO: при добавлении нового значения в категорию вызвать другую функцию
    #  TODO: При создании и добавлении вызывать 1 и ту же функцию
    # Покрасить в цвет таблицы, добавить строку в случае чего
    pass
