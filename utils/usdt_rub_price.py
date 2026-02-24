import aiohttp
import asyncio
import re
import time
from bs4 import BeautifulSoup
from data.config import percent_buy, percent_sell, dexpay

# --- НАСТРОЙКИ КЭША ---
# Мы будем хранить данные в памяти, чтобы не долбить сайт запросами каждую секунду.
# Это ускорит ответ бота до 0.001 секунды, если данные свежие.
CACHE = {
    "data": None,  # Здесь будет лежать результат
    "timestamp": 0  # Время последнего обновления
}
CACHE_TTL = 60 * 5  # Время жизни кэша в секундах (например, 5 минут)


async def get_exchange_rates(url="https://coinmarketcap.com/currencies/usual-usd/usd0/rub/"):
    """
    Асинхронная функция с кэшированием.
    Возвращает словарь с курсами или None.

    Проценты разницы находятся в конфиг файле
    Курс для покупки берется с сайта dexpay
    Курс для продажи берется с сайта coinmarketcap
    """

    # 1. ПРОВЕРКА КЭША
    # Если данные есть и они свежие (прошло меньше CACHE_TTL секунд), отдаем их сразу.
    current_time = time.time()
    if CACHE["data"] and (current_time - CACHE["timestamp"] < CACHE_TTL):
        return CACHE["data"]

    # 2. АСИНХРОННЫЙ ЗАПРОС
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status != 200:
                    print(f"Ошибка: статус ответа {response.status}")
                    return None
                html = await response.text()

        # 3. ПАРСИНГ (выполняется быстро, но можно вынести в отдельный поток, если HTML огромный)
        soup = BeautifulSoup(html, 'html.parser')

        price_meta = soup.find("meta", property="og:description")
        if not price_meta:
            return None

        content = price_meta["content"]
        match = re.search(r"(\d+[\.,]\d+)", content)

        if match:
            current_price_dexpay = float(await dexpay.get_exchange_rate())  # dexpay
            current_price_coinmarketcap = float(match.group(1).replace(',', '.'))  # coinmarketcap

            sotaya_buy = percent_buy / 100
            sotaya_sell = percent_sell / 100

            buy_price = current_price_dexpay * (1 + sotaya_buy)
            sell_price = current_price_coinmarketcap * (1 - sotaya_sell)

            result = {
                "курс": round(current_price_coinmarketcap, 2),
                "покупка": round(buy_price, 2),
                "продажа": round(sell_price, 2)
            }

            # Сохраняем в кэш
            CACHE["data"] = result
            CACHE["timestamp"] = current_time

            return result

        return None

    except Exception as e:
        # Если произошла ошибка, можно попробовать вернуть старый кэш, если он есть
        print(f"Ошибка парсинга: {e}")
        if CACHE["data"]:
            return CACHE["data"]
        return None




