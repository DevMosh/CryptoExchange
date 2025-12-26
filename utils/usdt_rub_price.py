import requests
from bs4 import BeautifulSoup
import re

from data.config import percent_buy, percent_sell


def get_exchange_rates(url="https://coinmarketcap.com/currencies/usual-usd/usd0/rub/"):
    """
    Универсальная функция для парсинга курса с CoinMarketCap.
    Подходит для https://coinmarketcap.com/currencies/tether/usdt/rub/
    и для https://coinmarketcap.com/currencies/usual-usd/usd0/rub/
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        price_meta = soup.find("meta", property="og:description")
        if not price_meta:
            return None

        content = price_meta["content"]

        # Регулярка ищет число (целое или с точкой/запятой)
        match = re.search(r"(\d+[\.,]\d+)", content)

        if match:
            # Извлекаем реальный курс
            current_price = float(match.group(1).replace(',', '.'))

            # Переводим процент в коэффициент (например, 8 станет 0.08)
            sotaya_buy = percent_buy / 100
            sotaya_sell = percent_sell / 100

            # Расчеты на основе вашего процента
            buy_price = current_price * (1 + sotaya_buy)  # Покупка (вычитаем %)
            sell_price = current_price * (1 - sotaya_sell)  # Продажа (прибавляем %)

            return {
                "курс": round(current_price, 2),  # Реальный курс
                "покупка": round(buy_price, 2),  # Курс для покупки
                "продажа": round(sell_price, 2)  # Курс для продажи
            }

        return None

    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return None