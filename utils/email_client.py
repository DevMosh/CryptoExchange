import aiohttp
import logging
from typing import Optional

# Настройка логгераcl
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResendEmailClient:
    """
    Клиент для отправки писем через Resend API.
    """
    API_URL = "https://api.resend.com/emails"

    def __init__(self, api_key: str, sender_email: str, sender_name: str = "My Service"):
        """
        :param api_key: Ваш API ключ Resend (re_...)
        :param sender_email: Email отправителя. ВАЖНО: Должен быть на домене notifications.escotrust.ru
                             (например: no-reply@notifications.escotrust.ru)
        :param sender_name: Имя отправителя
        """
        self.api_key = api_key
        # Resend принимает формат: "Имя <email@domain.com>"
        self.from_header = f"{sender_name} <{sender_email}>"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def send_verification_code(self, to_email: str, code: str) -> bool:
        """
        Специальный метод для отправки кода подтверждения.
        """
        subject = "Ваш код подтверждения"
        html_content = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>Здравствуйте!</h2>
            <p>Ваш код для подтверждения почты ESCO:</p>
            <h1 style="color: #4CAF50; letter-spacing: 5px;">{code}</h1>
            <p>Если это были не вы, просто проигнорируйте это письмо.</p>
        </div>
        """
        return await self._send_request(to_email, subject, html_content)

    async def send_custom_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        Универсальный метод для отправки любого HTML письма.
        """
        return await self._send_request(to_email, subject, html_content)

    async def _send_request(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        Внутренний метод, выполняющий HTTP запрос к Resend.
        """
        payload = {
            "from": self.from_header,
            "to": [to_email],  # Resend принимает список строк
            "subject": subject,
            "html": html_content
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.API_URL, headers=self.headers, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Письмо успешно отправлено на {to_email}. ID: {data.get('id')}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Ошибка Resend API ({response.status}): {error_text}")
                        return False
        except Exception as e:
            logger.error(f"❌ Критическая ошибка соединения: {e}")
            return False