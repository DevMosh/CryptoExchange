from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardMarkup

from keyboards.inline import get_buy_sell_keyboard
from keyboards.reply import start_keyboard
from utils.usdt_rub_price import get_exchange_rates

router = Router()

class usdt_rub(StatesGroup):
    rub_usdt = State()

@router.message(CommandStart(), StateFilter("*"))
async def start(message: Message, state: FSMContext):
    usdt_rub_price = get_exchange_rates()
    await message.answer(f"""<b>Добрый день, {message.from_user.first_name}!</b>
    
⚡ EscoEX — бот для обмена USDT на рубли без P2P и обменников.""",
                         reply_markup=start_keyboard())


@router.message(F.text == "Обмен 💱")
async def exchange(message: Message, state: FSMContext):
    await message.answer(f"""<b>Курс <u>EscoEX</u>:</b>
Покупка ≈ {get_exchange_rates()['покупка']} ₽
Продажа ≈ {get_exchange_rates()['продажа']} ₽
""", reply_markup=get_buy_sell_keyboard())


@router.message(F.text == "История 🗄")
async def history(message: Message, state: FSMContext):
    await message.answer("У Вас пока нет активных или успешных обменов.")


@router.message(F.text == "Поддержка 📧")
async def support(message: Message, state: FSMContext):
    await message.answer("Возникли проблемы или просто есть вопросы? Пишите - @khsv500")