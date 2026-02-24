import asyncio
import hashlib
import random
from decimal import Decimal

from aiogram import Router, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from sqlalchemy import select

from data.config import client, dexpay
from database.connect import async_session
from database.models import User
from database.requests.add import add_user
from database.requests.get import get_user, check_email_exists
from keyboards.inline import get_buy_sell_keyboard, get_cancel_keyboard
from keyboards.reply import start_keyboard
from utils.usdt_rub_price import get_exchange_rates
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext

from utils.validation import is_valid_email

router = Router()

class Usdt_rub(StatesGroup):
    rub_usdt = State()

# Состояние для регистрации
class Registration(StatesGroup):
    waiting_for_email = State()
    waiting_for_code = State()
    waiting_for_terms = State()


# --- ХЕНДЛЕР 1: Запуск бота ---
@router.message(CommandStart(), StateFilter("*"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id

    # Проверяем, есть ли пользователь в базе (прошел ли он уже регистрацию)
    async with async_session() as session:
        result = await session.execute(select(User).where(User.user_id == user_id))
        existing_user = result.scalar()

    if existing_user:
        # СЦЕНАРИЙ: СТАРЫЙ ПОЛЬЗОВАТЕЛЬ (уже подтвержден)
        await message.answer(
            f"<tg-emoji emoji-id='5240428351063081133'>👍</tg-emoji> <b>С возвращением, {message.from_user.first_name}!</b>\n\n",
            reply_markup=start_keyboard()
        )

    else:
        # СЦЕНАРИЙ: НОВЫЙ ПОЛЬЗОВАТЕЛЬ (или не закончил регистрацию)
        await message.answer(
            f"<tg-emoji emoji-id='5474371208176737086'>👍</tg-emoji>\n\n",
            reply_markup=ReplyKeyboardRemove()
        )
        await message.answer(
            f"<b>Добро пожаловать в EscoEX!</b>\n\n"
            f"Для завершения регистрации, пожалуйста, введите ваш <b>Email</b>:\n", reply_markup=get_cancel_keyboard()
        )
        # Ждем ввод почты
        await state.set_state(Registration.waiting_for_email)


# --- ХЕНДЛЕР 2: Получаем Email, генерируем код и отправляем ---
@router.message(Registration.waiting_for_email)
async def process_email(message: Message, state: FSMContext):
    # Приводим к нижнему регистру
    email = message.text.strip().lower()

    # 1. Валидация формата
    if not is_valid_email(email):
        await message.answer(
            "⚠️ <b>Некорректный формат почты.</b>\n\n"
            "Пример: <i>name@example.com</i>",
            reply_markup=get_cancel_keyboard()  # Добавил кнопку отмены и сюда, на случай ошибки
        )
        return

    # Проверка существования почты
    is_taken = await check_email_exists(email)
    if is_taken:
        await message.answer(
            "🚫 <b>Этот Email уже зарегистрирован!</b>\n\n"
            "Пожалуйста, используйте другую почту.",
            reply_markup=get_cancel_keyboard() # И сюда, чтобы можно было выйти
        )
        return

    # 2. Сообщение о процессе
    msg = await message.answer("⏳ Генерирую код и отправляю письмо...")

    # 3. Генерация кода
    verification_code = str(random.randint(100000, 999999))

    try:
        # 4. Отправка
        is_sent = await client.send_verification_code(email, verification_code)

        if is_sent:
            # 5. Сохраняем в State
            await state.update_data(email=email, verification_code=verification_code)
            await state.set_state(Registration.waiting_for_code)

            # ВАЖНО: Добавляем клавиатуру с кнопкой "Отмена" сюда
            await msg.edit_text(
                f"✅ <b>Код отправлен на {email}</b>\n"
                f"<i>(Проверьте папку Спам, если письма нет)</i>\n\n"
                f"Введите 6 цифр из письма:",
                reply_markup=get_cancel_keyboard()
            )
        else:
            await msg.edit_text(
                "❌ Ошибка отправки письма. Попробуйте другой Email.",
                reply_markup=get_cancel_keyboard()
            )

    except Exception as e:
        await msg.edit_text(
            f"❌ Произошла ошибка при отправке: {e}",
            reply_markup=get_cancel_keyboard()
        )


# --- ХЕНДЛЕР 3: Проверяем код подтверждения ---
@router.message(Registration.waiting_for_code)
async def process_code(message: Message, state: FSMContext):
    user_code = message.text.strip()

    # Достаем данные, которые сохранили на прошлом шаге
    data = await state.get_data()
    correct_code = data.get("verification_code")
    email = data.get("email")

    # Сравниваем
    if user_code == correct_code:
        # --- УСПЕХ: Только сейчас записываем в БД ---
        await add_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            email=email
        )

        # Очищаем состояние
        await state.clear()

        await message.answer(
            f"🎉 <b>Почта подтверждена!</b>\n\n"
            f"Регистрация завершена. Добро пожаловать!",
            reply_markup=start_keyboard()
        )
        # добавь тут регистрацию юзера в dexpay
    else:
        # --- ОШИБКА: Код неверный ---
        await message.answer(
            "❌ <b>Неверный код.</b>\n\n"
            "Попробуйте еще раз или введите /start для смены почты."
        )


@router.message(F.text == "Обмен 💱")
async def exchange(message: Message, state: FSMContext):
    msg = await message.answer(f"""<b>Курс <u>EscoEX</u>:</b>""", reply_markup=get_buy_sell_keyboard())

    usdt_rub_price = await get_exchange_rates()
    await msg.edit_text(f"""<b>Курс <u>EscoEX</u>:</b>
Покупка ≈ {usdt_rub_price['покупка']} ₽
Продажа ≈ {usdt_rub_price['продажа']} ₽
    """, reply_markup=get_buy_sell_keyboard())

    dexpay_users = dict((await dexpay.get_all_users())[0])
    print(dexpay_users)

    # email = "test@example.com"
    customer_uuid = "custom-client-id-001"
    await message.answer(f"{await dexpay.create_kyc_link(dexpay_user_id='d042c90d62')}")


@router.message(F.text == "История 🗄")
async def history(message: Message, state: FSMContext):
    await message.answer("У Вас пока нет активных или успешных обменов.")


@router.message(F.text == "Поддержка 📧")
async def support(message: Message, state: FSMContext):
    await message.answer("Возникли проблемы или просто есть вопросы? Пишите - @")


# Обработчик нажатия на кнопку "Отмена" (callback_data="cancel_payment")
@router.callback_query(F.data == "cancel_payment")
async def cancel_registration(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()

    if current_state is None:
        await callback.answer("Нет активной регистрации.")
        return

    # Сбрасываем состояние
    await state.clear()

    await callback.message.edit_text(
        "❌ Регистрация отменена.\n\n"
        "Чтобы начать заново, отправьте команду /start"
    )
    await callback.answer()