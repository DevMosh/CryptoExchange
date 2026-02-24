import hashlib
import aiohttp
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP
from typing import Optional, Dict, Any


class DexpayClient:
    # ИСПРАВЛЕНИЕ 1: Верный URL из документации
    def __init__(self, api_token: str, base_url: str = "https://esco.dexpay.ru/api"):
        self.base_url = base_url
        self.auth_token = hashlib.sha256(api_token.encode()).hexdigest()

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }

    async def _request(self, method: str, endpoint: str, data: Optional[dict] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, json=data, headers=self._get_headers()) as response:
                resp_json = await response.json()
                print(resp_json)

                # Обработка ошибок
                if not resp_json.get("success"):
                    error_msg = resp_json.get("message", "Unknown Error")
                    error_details = resp_json.get("errors", [])
                    # Логирование или выброс исключения с деталями
                    raise Exception(f"Dexpay API Error: {error_msg} | Details: {error_details}")

                return resp_json.get("data")

    async def register_user(self, email: str, customer_id: str) -> str:
        endpoint = "/v1/auth/login"
        payload = {
            "email": email,
            "customer_id": customer_id  # [cite: 88]
        }
        data = await self._request("POST", endpoint, payload)
        return data["id"]

    # --- Получение списка всех пользователей [cite: 112-123] ---
    async def get_all_users(self) -> dict:
        """
        Возвращает список зарегистрированных пользователей.
        Метод: GET /v1/users
        """
        # В документации указано, что возвращается объект с полями 'count' и 'data'
        return await self._request("GET", "/v1/users")

    # --- Получение списка всех ордеров
    async def get_all_orders(self) -> dict:
        """
        Возвращает список зарегистрированных пользователей.
        Метод: GET /v1/orders
        """
        # В документации указано, что возвращается объект с полями 'count' и 'data'
        return await self._request("GET", "/v1/orders")

    async def get_exchange_rate(self) -> Decimal:
        url = "https://ltd.dexpay.ru/getExchangeRate"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to fetch rates. Status: {response.status}")

                data = await response.json()
                raw_rate = data.get("rate")

                if raw_rate is None:
                    # ВАЖНО: Добавим вывод ошибки, чтобы видеть, что пришло на самом деле
                    raise ValueError(f"Курс не найден в ответе API. Ответ: {data}")

                return Decimal(str(raw_rate))

    async def create_order(
            self,
            user_id: str,  # Внутренний ID Dexpay (asd123)
            rub_amount: Decimal,
            wallet_address: str,
            email: str,  # Verified Email [cite: 615]
            customer_id: str,  # Telegram ID
            user_ip: str,  # Реальный IP [cite: 624]
            network_code: str = "TRC20",
            network_fee_usdt: Decimal = Decimal("1.0")
    ):
        rate = await self.get_exchange_rate()
        network_price_rub = network_fee_usdt * rate

        sum_in_formatted = float(rub_amount.quantize(Decimal("0.01"), rounding=ROUND_FLOOR))
        network_price_formatted = str(network_price_rub.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

        # --- НОВЫЕ ТРЕБОВАНИЯ К ПЕЙЛОАДУ [cite: 613-626] ---
        payload = {
            "paymentData": {
                "user_id": user_id,
                "sum_in": sum_in_formatted,
                "rate": str(rate),
                "wallet": wallet_address,
                "network": {
                    "price": network_price_formatted,
                    "value": network_code
                },
                "email": email,
                "customer_id": customer_id,

                # Флаг согласия с офертой (Обязателен) [cite: 625]
                "terms_accepted": True
            },

            # Расширенный фингерпринт для антифрода [cite: 616]
            "fingerprint": {
                "user_ip": user_ip,  # [cite: 624]
                "user_agent": "TelegramBot/1.0 (Android; IOS)",  # [cite: 617]
                "language": "ru-RU",  # [cite: 618]
                "timezone": "+03:00",  # [cite: 619]

                # Для бота эти поля можно хардкодить или генерировать,
                # так как у нас нет браузерного Canvas
                "screen_resolution": "1920x1080",  # [cite: 620]
                "canvas_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",  # [cite: 621]
                "features_hash": "d41d8cd98f00b204e9800998ecf8427e",  # [cite: 622]
                "behavior_delay": 150  # [cite: 623]
            }
        }

        response = await self._request("POST", "/v1/orders/create", payload)
        return response["data"]

    async def get_order_status(self, order_id: str):
        endpoint = f"/v1/orders/status/{order_id}"
        return await self._request("GET", endpoint)

    # --- Верификация (KYC) ---

    # --- Верификация (KYC) ---

    async def create_kyc_link(self, dexpay_user_id: str) -> Dict[str, Any]:
        """
        Создает ссылку для верификации.
        :param dexpay_user_id: Внутренний ID пользователя в системе Dexpay (полученный при регистрации)
        Метод: POST /v1/users/kyc/create
        """
        endpoint = "/v1/users/kyc/create"

        # Согласно описанию ошибок, обязателен user_id.
        # user_id здесь - это ID внутри Dexpay (напр. "asd123")
        payload = {
            "user_id": dexpay_user_id
        }

        # Ответ сервера [cite: 265-270]:
        # {
        #   "id": "asd123",
        #   "link": "https://...",
        #   "status": "PROCESS",
        #   "customer_id": "твой_tg_id"
        # }
        return await self._request("POST", endpoint, payload)

    async def get_kyc_status(self, dexpay_user_id: str) -> str:
        """
        Проверяет статус верификации.
        :param dexpay_user_id: Внутренний ID пользователя в системе Dexpay
        Метод: GET /v1/users/kyc/status
        """
        # Передаем user_id в строке запроса [cite: 273]
        endpoint = f"/v1/users/kyc/status?user_id={dexpay_user_id}"

        data = await self._request("GET", endpoint)

        # Возвращает статус: "NONE" | "PROCESS" | "REJECTED" | "APPROVED" [cite: 279]
        return data.get("status")




