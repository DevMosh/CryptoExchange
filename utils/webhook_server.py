import os
import logging
from fastapi import FastAPI, Request, HTTPException, Header
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# Импортируем твои функции для работы с БД
from database.requests.set import set_user_kyc_status, update_order_status
from database.requests.get import get_user_by_dexpay_id

load_dotenv()

app = FastAPI(title="Dexpay Webhooks Listener")

# Инициализируем бота для отправки уведомлений
bot = Bot(token=os.getenv('BOT_TOKEN'), default=DefaultBotProperties(parse_mode='html'))

# http://webhook.escotrust.ru/webhook/dexpay
@app.post("/webhook/dexpay")
async def dexpay_webhook(request: Request):
    # Опционально: можно добавить проверку токена (Authorization: Bearer SHA256(API_TOKEN))
    # auth_header = request.headers.get("Authorization")

    try:
        data = await request.json()
        event_type = data.get("event")
        logging.info(f"📥 Получен вебхук {event_type}: {data}")

        # ==========================================
        # 1. ВЕБХУК: KYC (kyc.status)
        # ==========================================
        if event_type == "kyc.status":
            dexpay_user_id = data.get("user_id")
            customer_id = data.get("customer_id")  # Это наш Telegram ID, который мы передавали при регистрации
            new_status = data.get("status")  # NONE || PROCESS || REJECTED || APPROVED

            # Поскольку в customer_id мы передавали Telegram ID, можем использовать его напрямую:
            if customer_id and new_status:
                tg_user_id = int(customer_id)
                await set_user_kyc_status(tg_user_id, new_status)

                if new_status == "APPROVED":
                    await bot.send_message(
                        tg_user_id,
                        "🎉 <b>Верификация пройдена!</b>\n\nТеперь вам доступны все операции."
                    )
                elif new_status == "REJECTED":
                    await bot.send_message(
                        tg_user_id,
                        "❌ <b>Ошибка верификации.</b>\n\nВаши документы отклонены. Пожалуйста, пройдите проверку заново."
                    )
            return {"status": "success", "message": "KYC processed"}

        # ==========================================
        # 2. ВЕБХУК: ОПЛАТА ЗАЯВКИ (order.status)
        # ==========================================
        elif event_type == "order.status":
            order_id = data.get("order_id")
            status = data.get("status")  # pending | completed | failed | paid

            order = await update_order_status(order_id, status)

            if order and status == "paid":
                await bot.send_message(
                    order.user_id,
                    f"✅ <b>Оплата получена!</b>\n\n"
                    f"Мы успешно получили ваши рубли по заявке <b>#{order.id}</b>.\n"
                    f"⏳ Ожидайте отправки USDT на ваш кошелек..."
                )
            return {"status": "success", "message": "Order processed"}

        # ==========================================
        # 3. ВЕБХУК: ВЫВОД USDT (withdraw.status)
        # ==========================================
        elif event_type == "withdraw.status":
            order_id = data.get("order_id")
            status = data.get("status")  # FAILED | COMPLETED
            tx_hash = data.get("tx_hash")

            order = await update_order_status(order_id, status, tx_hash)

            if order and status == "COMPLETED":
                # Ссылка на TronScan (если используешь TRC20)
                explorer_link = f"https://tronscan.org/#/transaction/{tx_hash}"

                await bot.send_message(
                    order.user_id,
                    f"🚀 <b>Заявка #{order.id} успешно выполнена!</b>\n\n"
                    f"💸 <b>{order.amount_usdt} USDT</b> отправлены на ваш кошелек.\n\n"
                    f"🔗 <a href='{explorer_link}'>Посмотреть транзакцию</a>\n\n"
                    f"Спасибо, что выбираете EscoEX!",
                    disable_web_page_preview=True
                )
            elif order and status == "FAILED":
                await bot.send_message(
                    order.user_id,
                    f"⚠️ <b>Проблема с заявкой #{order.id}</b>\n\n"
                    f"Ошибка при отправке USDT. Наша поддержка уже разбирается с этим."
                )
            return {"status": "success", "message": "Withdraw processed"}

        else:
            logging.warning(f"Неизвестный тип события: {event_type}")
            return {"status": "ignored"}

    except Exception as e:
        logging.error(f"🔥 Ошибка при обработке вебхука: {e}")
        # Возвращаем 500, чтобы Dexpay поставил запрос в очередь и попробовал снова (по их доке)
        raise HTTPException(status_code=500, detail="Internal Server Error")


# ==========================================
# 2. ЭНДПОИНТ ДЛЯ ДЕБАГА (Debug Webhook)
# ==========================================
@app.post("/webhook/dexpay/debug")
async def dexpay_debug_webhook(request: Request):
    """
    Отдельный адрес для локального дебага.
    Отправляется 1 раз, без подтверждения, без очереди/ретраев.
    """
    try:
        data = await request.json()
        event_type = data.get("event", "UNKNOWN_EVENT")

        # Просто красиво логируем всё, что пришло, чтобы анализировать структуру JSON
        logging.info(f"🛠 [DEBUG WEBHOOK] Событие: {event_type}")
        logging.info(f"🛠 [DEBUG WEBHOOK] Данные: {data}")

        return {"status": "success", "message": "Debug webhook received"}

    except Exception as e:
        logging.error(f"🔥 [DEBUG WEBHOOK] Ошибка при чтении: {e}")
        # Для дебаг-вебхука отдаем 200, так как Dexpay его не будет ретраить
        return {"status": "error", "message": str(e)}