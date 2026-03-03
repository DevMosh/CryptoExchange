import asyncio
import hashlib
import random
from decimal import Decimal

from aiogram import Router, F, types
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, ReplyKeyboardRemove, CallbackQuery
from sqlalchemy import select

from data.config import client, dexpay, terms, privacy, support_link
from database.connect import async_session
from database.models import User
from database.requests.add import add_user
from database.requests.get import get_user, check_email_exists, get_user_orders
from keyboards.inline import get_buy_sell_keyboard, get_cancel_keyboard, history_type_keyboard
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
            f"Отправляя свой Email, вы подтверждаете согласие с нашей <a href='{privacy}'>Политикой конфиденциальности</a> и <a href='{terms}'>Пользовательским соглашением</a>.\n\n"
            f"Для завершения регистрации, пожалуйста, введите ваш <b>Email</b>:",
            reply_markup=get_cancel_keyboard(), disable_web_page_preview=True
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
        msg = await message.answer("⏳ Проверяем данные и создаем аккаунт...")

        dexpay_id = None

        try:
            # 1. Проверяем, существует ли пользователь в Dexpay
            all_users = await dexpay.get_all_users()
            # Обрабатываем структуру ответа API Dexpay (список или словарь)
            users_list = all_users.get("data", []) if isinstance(all_users, dict) else all_users

            for d_user in users_list:
                if d_user.get("email") == email:
                    dexpay_id = d_user.get("id")
                    break

            # 2. Если пользователя нет, регистрируем его
            if not dexpay_id:
                dexpay_id = await dexpay.register_user(
                    email=email,
                    customer_id=str(message.from_user.id)
                )

        except Exception as e:
            await msg.edit_text(
                "❌ <b>Ошибка при связи с платежным шлюзом.</b>\n\n"
                "Пожалуйста, попробуйте позже или обратитесь в поддержку."
            )
            print(f"Dexpay Error: {e}")
            return

        # 3. Записываем пользователя в БД бота вместе с ID от Dexpay
        await add_user(
            user_id=message.from_user.id,
            username=message.from_user.username,
            email=email,
            dexpay_internal_id=dexpay_id  # Передаем новый параметр в БД
        )

        # Очищаем состояние
        await state.clear()

        # Удаляем сообщение "Проверяем данные..."
        try:
            await msg.delete()
        except Exception:
            pass

        # Отправляем новое сообщение с Reply-клавиатурой
        await message.answer(
            f"🎉 <b>Почта подтверждена!</b>\n\n"
            f"Регистрация завершена. Добро пожаловать!",
            reply_markup=start_keyboard()
        )
    else:
        # --- ОШИБКА: Код неверный ---
        await message.answer(
            "❌ <b>Неверный код.</b>\n\n"
            "Попробуйте еще раз или введите /start для смены почты."
        )


@router.message(F.text == "Операции 💱")
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
    # await message.answer(f"{await dexpay.create_kyc_link(dexpay_user_id='d042c90d62')}")


@router.message(F.text == "История 🗄")
async def history(message: types.Message, state: FSMContext):
    await message.answer(
        "Выберите тип операций для просмотра истории:",
        reply_markup=history_type_keyboard()
    )


@router.callback_query(F.data.in_(["history_buy", "history_sell"]))
async def show_history(callback: types.CallbackQuery):
    # Определяем тип из callback_data
    order_type = "buy" if callback.data == "history_buy" else "sell"
    type_text = "покупке" if order_type == "buy" else "продаже"

    # Делаем запрос в базу
    orders = await get_user_orders(callback.from_user.id, order_type)

    if not orders:
        await callback.message.edit_text(
            f"📭 У Вас пока нет истории операций по <b>{type_text}</b>.",
            parse_mode="HTML",
            reply_markup=history_type_keyboard()
        )
        return

    # Если заявки есть, формируем красивый список
    text = f"<b>Ваша история операций по {type_text}:</b>\n\n"

    for order in orders:
        # Форматируем дату (учитывая, что order.created_at - это datetime)
        date_str = order.created_at.strftime("%d.%m.%Y %H:%M")

        text += (
            f"🔹 <b>Заявка #{order.id}</b> | {date_str}\n"
            f"Сумма: {order.amount_usdt} USDT (≈ {order.amount_rub} ₽)\n"
            f"Статус: <i>{order.status}</i>\n"
            f"-----------------------\n"
        )

    # Редактируем сообщение, оставляя клавиатуру для переключения
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=history_type_keyboard()
    )


@router.message(F.text == "Поддержка 📧")
async def support(message: Message, state: FSMContext):
    await message.answer(
        "🛠 <b>Служба поддержки EscoEX</b>\n\n"
        "Возникли проблемы или есть вопросы по операции? Свяжитесь с нами:\n\n"
        f"💬 <b>Telegram:</b> @{support_link}\n"  # Укажи реальный юзернейм
        "📧 <b>Email:</b> support@escotrust.ru\n\n"  # Обязательно почта на вашем домене
        "<i>Мы отвечаем ежедневно с 10:00 до 22:00 (МСК).</i>",
        parse_mode="HTML"
    )


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