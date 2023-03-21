from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

admins = [6215929408]


router = Router()
router.message.filter(F.chat.id.in_(admins))


@router.message(CommandStart())
async def cmd_admin_start(message: Message):
    """Старт"""

    await message.answer(
        'Админ панель'
    )

@router.message(Command('get_opened'))
async def get_opened(message: Message):
    """Вывод открытых смен"""

    await message.answer(
        'Список открытых смен'
    )

@router.message(Command('get_closed'))
async def get_closed(message: Message):
    """Вывод закрытых смен"""

    await message.answer(
        'Спизок закрытых смен'
    )
