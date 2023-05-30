import datetime as dt
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.orm import sessionmaker

from keyboards.keyboards import (
    menu_button,
    inline_menu,
)
from .states import DefectiveProduct, Spendings, WorkshiftState
from .anonymous import workers_id
from models.models import User, WorkShift, Defective
from engine import engine


router = Router()
router.message.filter(F.chat.id.in_(workers_id))
router.callback_query.filter(F.chat.id.in_(workers_id))

Session = sessionmaker(bind=engine)


def workers():
    with Session() as session:
        users = session.query(User.telegram_id).all()
        global workers_id
        workers_id = set(users)


def check_registration(chat_id):
    """Проверка регистрации в БД"""
    with Session() as session:
        user = session.query(User)\
               .filter(User.telegram_id == chat_id).first()
        return True if user else False


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
    await state.update_data(status=direction)
    await state.set_state(WorkshiftState.shift)


@router.message(F.photo, WorkshiftState.shift)
async def open_photo(message: Message, state: FSMContext):
    """Получение фото смены"""
    data = await state.get_data()
    status = True if data['status'] == 'open' else False
    reply_status = 'открыта' if status else 'закрыта'
    photo = message.photo[-1].file_id
    with Session() as sess:
        user = sess.query(User).filter(User.telegram_id == message.chat.id)\
            .first()
        sess.add(
            WorkShift(
                user_id=user.id,
                photo=photo,
                status='open' if status else 'close',
                date=dt.datetime.now(),
                # Добавить проверку по shop_id
                shop_id='123'
            )
        )
        sess.commit()
    await message.reply(
        f'Смена {reply_status} \n'
        f'{message.date.time()} \n'
        f'{message.date.date()}'
    )
    await state.clear()


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
    with Session() as sess:
        user = sess.query(User).filter(User.telegram_id == message.chat.id)\
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


@router.message(Command('spendings'))
async def spendings(message: Message, state: FSMContext):
    """Траты"""

    await message.answer(
        'На что потрачено?'
    )
    await state.set_state(Spendings.purchaises)


@router.message(Spendings.purchaises, F.text)
async def purchaises(message: Message, state: FSMContext):
    """Получение списка трат"""

    await state.update_data(description=message.text)
    await message.answer(
        'Сколько потрачено рублей'
    )
    await state.set_state(Spendings.money_spent)


@router.message(
    Spendings.money_spent,
    F.text.func(lambda text: int(text) > 0)
)
async def money_spent(message: Message, state: FSMContext):
    """Получение количества потраченных денег"""

    await state.update_data(money=int(message.text))
    await message.answer(
        'Пришлите фото чека'
    )
    await state.set_state(Spendings.cash_receipt)


@router.message(Spendings.cash_receipt, F.photo)
async def cash_receipt(message: Message, state: FSMContext):
    """Получение фото чека"""

    photo = message.photo[-1].file_id
    await state.update_data(photo=photo)
    data = await state.get_data()
    with Session() as sess:
        user = sess.query(User).filter(User.telegram_id == message.chat.id)\
            .first()
        spent = Spendings(
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
    pass
