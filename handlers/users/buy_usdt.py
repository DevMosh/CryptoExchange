import asyncio

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from keyboards.inline import confirm_buy
from utils.usdt_rub_price import get_exchange_rates

router = Router()

class State_buy(StatesGroup):
    rub_usdt = State()

@router.callback_query(F.data == "action_buy")
async def process_buy(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Вы выбрали покупку USDT. Введите сумму:")
    await state.set_state(State_buy.rub_usdt)


@router.message(State_buy.rub_usdt)
async def buy_usdt_state(message: types.Message, state: FSMContext):
    usdt = float(message.text)
    if usdt < 40.0:
        await message.answer("Сумма обмена должна быть не менее 40$")
    else:
        msg = await message.answer('Проверяем курс')
        for i in range(1, 4):
            await asyncio.sleep(0.1)
            await msg.edit_text('Считаем'+('.'*i))

        await msg.edit_text(f"{usdt}$ ≈ {get_exchange_rates()['покупка']*usdt} ₽\n\n"
                            f"Будете покупать?", reply_markup=confirm_buy())
