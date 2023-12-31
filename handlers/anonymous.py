from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import User
from keyboards.keyboards import cities_inline, city_shops_inline, menu_button
from .states import Registration
from engine import async_engine, engine


router = Router()
workers_id = set()

router.message.filter(~F.chat.id.in_(workers_id))
router.callback_query.filter(~F.message.chat.id.in_(workers_id))

async_session = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    future=True
)

session = sessionmaker(engine)


def get_workers() -> None:
    global workers_id
    with session() as sess:
        users = sess.query(User)
        for user in users:
            workers_id.add(user.telegram_id)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    """Регистрация анонимного пользователя"""

    if message.chat.id not in workers_id:
        await message.answer(
            f'Привет, {message.chat.first_name}! '
            f'Тебе необходимо пройти регистрацию.'
        )
        await message.answer('Ваше имя')
        await state.set_state(Registration.first_name)


@router.message(Registration.first_name, F.text)
async def first_name(message: Message, state: FSMContext):
    """Получение имени"""

    await state.update_data(first_name=message.text)
    await message.answer(
        'Ваша Фамилия: '
    )
    await state.set_state(Registration.second_name)


@router.message(Registration.second_name, F.text)
async def second_name(message: Message, state: FSMContext):
    """Получение фамилии"""

    await state.update_data(second_name=message.text)
    await message.answer(
        'Город в котором Вы работаете: ',
        reply_markup=cities_inline()
    )
    print(await state.get_state())
    await state.set_state(Registration.city)


@router.callback_query(F.data.startswith('city'), Registration.city)
async def city_shop(callback: CallbackQuery, state: FSMContext):
    """Выбор города для работы"""
    city_id = callback.data.split('=')[1]
    await state.update_data(city_id=city_id)
    await callback.message.edit_text(
        text='Выберите магазин',
        reply_markup=city_shops_inline(city_id)
    )
    await state.set_state(Registration.shop)


@router.callback_query(Registration.shop, F.data.startswith('shop'))
async def shop(callback: CallbackQuery, state: FSMContext):
    """Получение города и завершение регистрации"""
    shop_id = callback.data.split('=')[1]
    username = callback.message.chat.username
    user_data = await state.get_data()
    async with async_session() as sess:
        user = User(
            first_name=user_data['first_name'],
            second_name=user_data['second_name'],
            telegram_username=username if username else None,
            telegram_id=callback.message.chat.id,
            shop_id=shop_id
        )
        await sess.add(user)
        await sess.commit()
    await callback.message.answer(
        'Регистрация завершена',
        reply_markup=menu_button()
    )
    await state.clear()
    global workers_id
    workers_id.add(callback.message.chat.id)
