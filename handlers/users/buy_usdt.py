import asyncio

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# Импорты (оставляем как были)
from keyboards.inline import confirm_buy, get_payment_rules_keyboard

from aiogram import Router, F, types
from aiogram.types import InlineQueryResultArticle, InputTextMessageContent
from utils.usdt_rub_price import get_exchange_rates  # Твой скрипт курса

router = Router()

class State_buy_usdt(StatesGroup):
    rub_usdt = State()
    get_address = State()


@router.inline_query(F.query.startswith("buy"))
async def handle_buy_query(inline_query: types.InlineQuery):
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
                id="buy_help",
                title="Введите сумму в USDT",
                description="Например: @bot buy 100",
                thumbnail_url="https://i.ibb.co/fGrLYsNj/image.png",
                thumbnail_width=100,
                thumbnail_height=100,
                input_message_content=InputTextMessageContent(
                    message_text="Напишите сумму после команды, например: @EscoTrustBot buy 100"
                )
            )
        )

    # Сценарий 2: Пользователь ввел что-то, пытаемся превратить в число
    else:
        try:
            usdt_amount = float(user_input.replace(',', '.'))

            # Получаем курс (предполагаем, что функция асинхронная)
            rates = await get_exchange_rates()
            rub_price = int(usdt_amount * rates['покупка'])

            # Формируем красивый результат с подсчетом
            results.append(
                InlineQueryResultArticle(
                    id=f"buy_{usdt_amount}",
                    title=f"Купить {usdt_amount} USDT",
                    description=f"💰 К оплате: ≈ {rub_price} RUB. Нажмите, чтобы продолжить.",
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
    rub_approx = int(usdt * rates['покупка'])
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
        f"✅ Выбрана сумма: <b>{usdt} USDT</b> ( ≈{rub_approx}₽)\n\n"
        "Введите адрес вашего USDT (TRC20) кошелька "
    ).replace(',', ' ')  # (Опционально) Делаем пробелы в тысячах (9 600 вместо 9,600)

    if last_address:
        msg_text += "или выберите последний использованный:"

    new_msg = await message.answer(msg_text, reply_markup=builder.as_markup(), parse_mode="HTML")

    await state.update_data(order_message_id=new_msg.message_id)
    await state.set_state(State_buy_usdt.get_address)

# --- Кнопка "Использовать последний адрес" ---
@router.callback_query(F.data == "use_last_address", State_buy_usdt.get_address)
async def process_use_last_address(callback: types.CallbackQuery, state: FSMContext):
    last_address = "TPAgKfYzRdK83Qocc4gXvEVu4jPKfeuer5"  # ТЕСТОВЫЙ АДРЕС
    # Тут удалять сообщение юзера не нужно, это callback
    await finalize_order_creation(callback.message, state, last_address)
    await callback.answer()


# --- Ручной ввод адреса ---
@router.message(State_buy_usdt.get_address)
async def process_manual_address(message: types.Message, state: FSMContext):
    # Удаляем сообщение с адресом, который скинул юзер
    try:
        await message.delete()
    except:
        pass

    address = message.text
    if len(address) < 10:
        err = await message.answer("⚠️ Слишком короткий адрес.")
        await asyncio.sleep(3)
        try:
            await err.delete()
        except:
            pass
        return

    # Передаем message, но работать будем с сохраненным ID внутри функции
    await finalize_order_creation(message, state, address)


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

        rub_price = (await get_exchange_rates())['покупка'] * usdt

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



@router.callback_query(F.data == "confirm_buy_usdt")
async def confirm_buy_usdt(query: types.CallbackQuery, state: FSMContext):
    await query.message.edit_text("""
<b>🔴 ВАЖНО: Правила безопасности</b>

Перед оплатой внимательно прочитайте. Эти правила защищают ваш платеж и аккаунт.

<b>💳 Оплата только с вашей карты</b>
Платежи от третьих лиц (друзей, родственников, покупателей) <b>запрещены</b>. При несовпадении ФИО система автоматически вернет деньги отправителю с удержанием комиссии <b>10%</b>. Криптовалюта выдана не будет.

<b>🚫 Запрет на дробление платежей</b>
Не пытайтесь разбить сумму на части (переводы до 15 000₽). Банки отслеживают суточные лимиты. За серию мелких переводов вам могут заблокировать банковский аккаунт по <b>115-ФЗ</b>. Платите всю сумму <b>одной транзакцией</b>.

<b>🔒 Ссылка привязана к устройству</b>
Не передавайте эту страницу другим людям. Ссылка защищена <b>Fingerprint</b>. При попытке открытия на другом устройстве транзакция будет помечена как «подозрительная» и заблокирована.

✅ <i>Нажимая кнопку ниже, я подтверждаю, что буду оплачивать со своей карты, и принимаю условия <a href="https://telegra.ph/PUBLICHNAYA-OFERTA-02-21-7">Публичной оферты и <a href="https://telegra.ph/POLITIKA-KONFIDENCIALNOSTI-02-21-89">Политики конфиденциальности</a>.</i>""",
reply_markup=get_payment_rules_keyboard())


@router.callback_query(F.data == "accept_rules_pay")
async def process_rules_accepted(callback: types.CallbackQuery, state: FSMContext):
    # Убираем часики загрузки
    await callback.answer()

    # 1. Достаем данные из стейта
    data = await state.get_data()
    usdt_amount = data.get('usdt_amount')
    wallet_address = data.get('wallet_address')

    # Если вдруг данные потерялись (например, перезагрузка бота)
    if not usdt_amount or not wallet_address:
        await callback.message.edit_text("⚠️ Ошибка: данные транзакции не найдены. Попробуйте начать заново.")
        return

    # 2. Пересчитываем сумму по актуальному курсу
    # (Курс мог измениться пока человек читал правила)
    current_rate = (await get_exchange_rates())['покупка']
    final_rub_amount = int(usdt_amount * current_rate)

    # !!! ЗДЕСЬ ТВОЯ ЛОГИКА ГЕНЕРАЦИИ ССЫЛКИ !!!
    # link = await db.create_payment(amount=final_rub_amount, ...)
    payment_link = "https://escotrust.ru"

    # Формируем клавиатуру
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(text="🔄 Я оплатил", callback_data="check_payment_status"),
        types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")
    )

    # 3. Редактируем сообщение, подставляя все данные
    await callback.message.edit_text(
        text=(
            f"✅ <b>Правила приняты. Заявка создана.</b>\n\n"
            f"Покупка: <b>{usdt_amount} USDT</b>\n"
            f"На кошелек: <code>{wallet_address}</code>\n"
            f"Сумма к оплате: <code>{final_rub_amount} RUB</code>\n\n"
            f"🔗 <b>Ваша ссылка для оплаты:</b>\n"
            f"{payment_link}\n\n"
            f"<i>⚠️ Ссылка действительна 15 минут.</i>"
        ),
        parse_mode="HTML",
        reply_markup=builder.as_markup(),
        disable_web_page_preview=True
    )


# -------------------------------------------------------------------
# 2. Обработка отмены
# -------------------------------------------------------------------
@router.callback_query(F.data == "cancel_payment")
async def process_payment_cancel(callback: types.CallbackQuery):
    # Уведомляем пользователя всплывашкой
    await callback.answer("Создание оплаты отменено", show_alert=False)

    # Вариант А: Просто удалить сообщение с правилами (чисто)
    await callback.message.delete()

    # Вариант Б: Отредактировать текст на "Отменено" (если нужно оставить историю)
    # await callback.message.edit_text("❌ Оплата отменена.")

    # Если нужно вернуть пользователя в главное меню, можно вызвать функцию меню здесь
    # await show_main_menu(callback.message)


# -------------------------------------------------------------------
# 3. Обработка кнопки "Я оплатил"
# -------------------------------------------------------------------
@router.callback_query(F.data == "check_payment_status")
async def process_check_payment(callback: types.CallbackQuery):
    # !!! ЗДЕСЬ ТВОЯ ЛОГИКА ПРОВЕРКИ ОПЛАТЫ !!!
    # Например: status = await crypto_api.check_transaction(user_id=callback.from_user.id)

    # Для примера имитируем ситуацию:
    # Поменяй на True, чтобы протестировать успешную оплату
    payment_received = False

    if not payment_received:
        # СЦЕНАРИЙ 1: Деньги еще не пришли
        # show_alert=True покажет окошко по центру экрана, которое нужно закрыть кнопкой ОК.
        # Это лучше, чем просто текст, потому что пользователь понимает, что бот проверил, но денег нет.
        await callback.answer(
        "⏳ Оплата пока не найдена.\n\n"
        "Транзакции в блокчейне могут занимать от 1 до 15 минут. "
        "Подождите немного и нажмите кнопку еще раз.",
        show_alert=True
        )

    else:
        # СЦЕНАРИЙ 2: Оплата прошла успешно
        await callback.answer() # Закрываем часики загрузки

        # Начисляем баланс в БД
        # await db.add_balance(user_id, amount)

        # Сообщаем об успехе
        await callback.message.edit_text(
        text=(
        "✅ <b>Оплата успешно зачислена!</b>\n\n"
        "Средства добавлены на ваш баланс. "
        "Можете пользоваться сервисом."
        ),
        parse_mode="HTML",
        # Можно добавить кнопку "В главное меню"
        reply_markup=None
        )