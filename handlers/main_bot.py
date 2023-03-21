from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove


router = Router()


@router.message(Command('start'))
async def cmd_start(message: Message):
    await message.answer(
        'Добро пожаловать!',
        reply_markup=ReplyKeyboardRemove()
    )