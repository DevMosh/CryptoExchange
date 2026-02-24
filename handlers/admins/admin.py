import asyncio
from datetime import datetime

from aiogram import Router, F, types
from aiogram.enums import ContentType
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message

from data.config import admins
from database.requests.get import get_all_user_ids, get_user_count, get_user_active_count, get_all_users_active_ids

from database.requests.set import set_user_active_status

admin_router = Router()


class Admin(StatesGroup):
    rassylka = State()
    rassylka_activ = State()


@admin_router.message((F.text == '/send') & (F.from_user.id.in_(admins)))
async def send_message_users(message: Message, state: FSMContext):
    await message.reply('Отправьте публикацию для рассылки по всем пользователям:\n\n'
                        'Отмена - /start')
    await state.set_state(Admin.rassylka)


@admin_router.message(Admin.rassylka)
async def answer_textrassylka(message: types.Message, state: FSMContext):
    startTime = datetime.now()
    users = await get_all_user_ids()
    j = 0
    msg = await message.reply(f'Рассылка отправлена \n'
                              f'В базе {len(users)} \n'
                              f'Удалили бота {j}')
    for user in users:
        try:
            await asyncio.sleep(0.01)
            await message.copy_to(chat_id=user, reply_markup=message.reply_markup)
            await set_user_active_status(user_id=user, status=True)
        except:
            await set_user_active_status(user_id=user, status=False)
            j += 1
            continue
        await state.clear()

    await msg.edit_text(f'Рассылка отправлена \n'
                        f'<b>В базе:</b> {len(users)} \n'
                        f'<b>Удалили бота:</b> {j} \n'
                        f'<b>Активных пользователей:</b> {len(users) - j}')
    await message.answer(f"Рассылка отправлена всем пользователям! \n"
                         f"Это заняло: {datetime.now() - startTime}")
    await state.clear()



@admin_router.message((F.text == '/send_activ') & (F.from_user.id.in_(admins)))
async def send_message_users(message: Message, state: FSMContext):
    await message.reply('Отправьте публикацию для рассылки только по активным:\n\n'
                        'Отмена - /start')
    await state.set_state(Admin.rassylka_activ)


@admin_router.message(Admin.rassylka_activ)
async def answer_textrassylka(message: types.Message, state: FSMContext):
    startTime = datetime.now()
    users = await get_all_users_active_ids()
    j = 0
    msg = await message.reply(f'Рассылка отправлена \n'
                              f'В базе {len(users)} \n'
                              f'Удалили бота {j}')
    for user in users:
        try:
            await asyncio.sleep(0.01)
            await message.copy_to(chat_id=user, reply_markup=message.reply_markup)
            await set_user_active_status(user_id=user, status=True)
        except:
            await set_user_active_status(user_id=user, status=False)
            j += 1
            continue
        await state.clear()

    await msg.edit_text(f'Рассылка отправлена \n'
                        f'<b>В базе:</b> {len(users)} \n'
                        f'<b>Удалили бота:</b> {j} \n'
                        f'<b>Активных пользователей:</b> {len(users) - j}')
    await message.answer(f"Рассылка отправлена всем пользователям! \n"
                         f"Это заняло: {datetime.now() - startTime}")
    await state.clear()


@admin_router.message((F.text == '/admin') & (F.from_user.id.in_(admins)), StateFilter("*"))
async def stat(message: types.Message, state: FSMContext):
    await state.clear()
    users_count = await get_user_count()
    users_count_active = await get_user_active_count()
    await message.answer(f'Пользователей: {users_count}\n'
                         f'Активных: {users_count_active}\n\n'
                         f'Отправить рассылку всем - /send\n'
                         f'Отправить рассылку активным - /send_activ\n')