
import asyncio

from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

from keyboards.inline import confirm_buy, get_payment_rules_keyboard

from aiogram import Router, F, types
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent
from utils.usdt_rub_price import get_exchange_rates  # Твой скрипт курса

router = Router()


class State_sell_usdt(StatesGroup):
    usdt_rub = State()


@router.callback_query(F.data == "action_sell")
async def process_sell(callback: types.CallbackQuery):
    await callback.message.edit_text("Вы выбрали продажу USDT. Введите сумму:")


@router.inline_query(F.query.startswith("sell"), StateFilter("*"))
async def handle_buy_query(inline_query: types.InlineQuery, state: FSMContext):
    await state.clear()
    query = inline_query.query

    # Пытаемся получить текст после "buy ". Например, из "buy 100" получаем "100"
    # Если просто "buy", то part будет пустой
    parts = query.split(maxsplit=1)
    user_input = parts[1] if len(parts) > 1 else ""

    results = []

    # Сценарий 1: Пользователь еще не ввел сумму или ввел ерунду
    if not user_input:
        results.append(
            InlineQueryResultArticle(
                id="sell_help",
                title="Введите сумму в USDT",
                description="Например: @bot sell 100",
                thumbnail_url="https://i.ibb.co/nMWvTcsP/unnamed.jpg",
                thumbnail_width=100,
                thumbnail_height=100,
                input_message_content=InputTextMessageContent(
                    message_text="Напишите сумму после команды, например: @EscoTrustBot sell 100"
                )
            )
        )

    # Сценарий 2: Пользователь ввел что-то, пытаемся превратить в число
    else:
        try:
            usdt_amount = float(user_input.replace(',', '.'))

            # Получаем курс (предполагаем, что функция асинхронная)
            rates = await get_exchange_rates()
            rub_price = int(usdt_amount * rates['продажа'])

            # Формируем красивый результат с подсчетом
            results.append(
                InlineQueryResultArticle(
                    id=f"buy_{usdt_amount}",
                    title=f"Продать {usdt_amount} USDT",
                    description=f"💰 Получите: ≈ {rub_price} RUB. Нажмите, чтобы продолжить.",
                    thumbnail_url="https://i.ibb.co/fGrLYsNj/image.png",
                    thumbnail_width=100,
                    thumbnail_height=100,
                    # ВАЖНО: Вот это сообщение отправится в чат при клике
                    input_message_content=InputTextMessageContent(
                        message_text=f"🛒 Создать заявку на покупку: {usdt_amount} USDT"
                    )
                )
            )
        except ValueError:
            # Если ввели не число
            results.append(
                InlineQueryResultArticle(
                    id="buy_error",
                    title="Ошибка ввода",
                    description="Пожалуйста, введите корректное число",
                    thumbnail_url="https://i.ibb.co/fGrLYsNj/image.png",
                    thumbnail_width=100,
                    thumbnail_height=100,
                    input_message_content=InputTextMessageContent(
                        message_text="Нужно ввести числовое значение."
                    )
                )
            )

    # cache_time=1, чтобы при вводе каждой новой цифры пересчитывалось быстро
    await inline_query.answer(results, is_personal=True, cache_time=1)


@router.message(F.text.startswith("🛒 Создать заявку на покупку:"))
async def process_instant_buy_from_inline(message: types.Message, state: FSMContext):
    # 1. Парсим сумму
    try:
        text_amount = message.text.split(":")[1].replace("USDT", "").strip()
        usdt = float(text_amount)
    except (IndexError, ValueError):
        await message.answer("⚠️ Ошибка обработки суммы. Попробуйте снова.")
        return

    # 2. Удаляем сообщение юзера
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    # 3. Проверка лимита
    if usdt < 40.0:
        msg = await message.answer("⚠️ Сумма обмена должна быть не менее 40$")
        await asyncio.sleep(3)
        try:
            await msg.delete()
        except:
            pass
        return

    await state.update_data(usdt_amount=usdt)

    # --- НОВОЕ: Получаем курс и считаем рубли ---
    rates = await get_exchange_rates()
    # Считаем сумму (округляем до целого через int или .0f)
    rub_approx = int(usdt * rates['продажа'])
    # --------------------------------------------

    last_address = "TPAgKfYzRdK83Qocc4gXvEVu4jPKfeuer5"  # Заглушка

    builder = InlineKeyboardBuilder()
    if last_address:
        builder.row(types.InlineKeyboardButton(
            text=f"Использовать {last_address[:6]}...{last_address[-4:]}",
            callback_data="use_last_address"
        ))

    # --- НОВОЕ: Обновленный текст сообщения ---
    msg_text = (
        f"✅ Выбрана сумма: <b>{usdt} USDT</b> (≈{rub_approx}₽)\n\n"
        "Подтвердите создание  "
    ).replace(',', ' ')  # (Опционально) Делаем пробелы в тысячах (9 600 вместо 9,600)

    if last_address:
        msg_text += "или выберите последний использованный:"

    new_msg = await message.answer(msg_text, reply_markup=builder.as_markup(), parse_mode="HTML")

    await state.update_data(order_message_id=new_msg.message_id)
    await state.set_state(State_sell_usdt.get_address)


# --- Функция финализации (Анимация + Итог) ---
async def finalize_order_creation(message_obj: types.Message, state: FSMContext, wallet_address: str):
    await state.update_data(wallet_address=wallet_address)
    data = await state.get_data()
    usdt = data['usdt_amount']
    order_msg_id = data.get('order_message_id')

    # Если вдруг ID потерялся, берем ID текущего сообщения (если это callback)
    if not order_msg_id and message_obj.from_user.is_bot:
        order_msg_id = message_obj.message_id

    # Анимация "Считаем..."
    # Редактируем то самое сообщение по ID
    if order_msg_id:
        # Сначала ставим текст "Проверяем курс"
        await message_obj.bot.edit_message_text(
            text="⏳ Проверяем курс",
            chat_id=message_obj.chat.id,
            message_id=order_msg_id
        )

        for i in range(1, 4):
            await asyncio.sleep(0.3)  # Чуть быстрее
            await message_obj.bot.edit_message_text(
                text='Считаем' + ('.' * i),
                chat_id=message_obj.chat.id,
                message_id=order_msg_id
            )

        rub_price = (await get_exchange_rates())['продажа'] * usdt

        # Финальный текст
        await message_obj.bot.edit_message_text(
            text=(
                f"<b>Покупка:</b> {usdt} USDT\n"
                f"<b>Кошелек:</b> <code>{wallet_address}</code>\n"
                f"<b>К оплате:</b> ≈ {rub_price:.0f}₽\n\n"
                f"Для продолжения нажмите на кнопку оплатить 👇"
            ),
            chat_id=message_obj.chat.id,
            message_id=order_msg_id,
            reply_markup=confirm_buy(),
            parse_mode="HTML"
        )
    else:
        # Фолбэк, если что-то пошло совсем не так с ID
        await message_obj.answer("Ошибка интерфейса. Попробуйте заново /start")