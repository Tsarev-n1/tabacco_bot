from aiogram import Router, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

router = Router()

class DefectiveProduct(StatesGroup):
    get_video = State()
    get_title = State()
    get_product_id = State()


class Spendings(StatesGroup):
    get_purchaises = State()
    get_money_spent = State()
    get_cash_receipt = State()


class Registration(StatesGroup):
    get_first_name = State()
    get_second_name = State()
    get_city = State()


@router.message(CommandStart())
async def cmd_worker_start(message: Message, state: FSMContext):
    """Старт"""

    #Добавить регистрацию

    await message.answer(
        'Панель для работников'
    )
    state.clear()

@router.message(Command('open'), F.photo)
async def cmd_open(message: Message):
    """Открытие смены"""

    await message.reply(
        'Смена открыта'
    )

@router.message(Command('close'), F.photo)
async def cmd_close(message: Message):
    """Закрытие смены"""

    await message.reply(
        'Смена закрыта'
    )

@router.message(Command('defective'))
async def cmd_defective(message: Message, state: FSMContext):
    """Бракованный товар"""

    await message.answer(
        'Пришлите видео с товаром'
    )
    await state.set_state(DefectiveProduct.get_video)

@router.message(DefectiveProduct.get_video, F.video)
async def get_video(message: Message, state: FSMContext):
    """Получение видео с браком"""

    await message.answer(
        'Наименование товара'
    )
    await state.set_state(DefectiveProduct.get_title)

@router.message(DefectiveProduct.get_title)
async def get_title(message: Message, state: FSMContext):
    """Получить название бракованного товара"""

    await message.answer(
        'Артикул'
    )
    await state.set_state(DefectiveProduct.get_product_id)

@router.message(
    DefectiveProduct.get_product_id,
    F.text.func(lambda text: int(text) > 0)
)
async def get_product_id(message: Message, state: FSMContext):
    """Получить артикул бракованного товара"""

    await message.answer(
        'Запрос принят'
    )
    await state.clear()

@router.message(Command('spendings'))
async def get_spendings(message: Message, state: FSMContext):
    """Траты"""

    await message.answer(
        'На что потрачено?'
    )
    await state.set_state(Spendings.get_purchaises)

@router.message(Spendings.get_purchaises, F.text)
async def get_purchaises(message: Message, state: FSMContext):
    """Получение списка трат"""

    await message.answer(
        'Сколько потрачено рублей'
    )
    await state.set_state(Spendings.get_money_spent)

@router.message(
    Spendings.get_money_spent,
    F.text.func(lambda text: float(text) > 0)
)
async def get_money_spent(message: Message, state: FSMContext):
    """Получение количества потраченных денег"""

    #Добавить валидацию на Float

    await message.answer(
        'Пришлите фото чека'
    )
    await state.set_state(Spendings.get_cash_receipt)

@router.message(Spendings.get_cash_receipt, F.photo)
async def get_cash_receipt(message: Message, state: FSMContext):
    """Получение фото чека"""

    await message.answer(
        'Запрос принят'
    )
    await state.clear()

@router.message(Command('order'))
async def cmd_order(message: Message):
    """Запрос на заказ товара"""

    await message.answer(
        'Запрос принят'
    )

#Фильтр по id
#Передать доп параметры в state
@router.message(Command('registration'), ~F.chat.id.in_(users.id))
async def cmd_registration(message: Message, state: FSMContext):
    """Регистрация"""
    await message.answer(
        'Ваше имя: '
    )
    await state.set_state(Registration.get_first_name)

@router.message(Registration.get_first_name, F.text)
async def get_first_name(message: Message, state: FSMContext):
    """Получение имени"""

    await message.answer(
        'Ваша Фамилия: '
    )
    await state.set_state(Registration.get_second_name)

@router.message(Registration.get_second_name, F.text)
async def get_second_name(message: Message, state: FSMContext):
    """Получение фамилии"""

    await message.answer(
        'Город в котором Вы работаете: '
    )
    await state.set_state(Registration.get_city)

@router.message(Registration.get_city, F.text)
async def get_city(message: Message, state: FSMContext):
    """Получение города и завершение регистрации"""

    await message.answer(
        'Регистрация завершена'
    )
    await state.clear()
