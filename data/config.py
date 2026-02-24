import os

from dotenv import load_dotenv

from utils.dexpay import DexpayClient
from utils.email_client import ResendEmailClient

load_dotenv()

percent_buy = 2
percent_sell = 4.86

admins = [1881571115, 413056248, 407629539]


client = ResendEmailClient(
    api_key=os.getenv('RESENDEMAIL_API_TOKEN'),
    sender_email="code@notifications.escotrust.ru",
    sender_name="EscoTrust Bot"
)

dexpay = DexpayClient(
    api_token=os.getenv('DEXPAY_API_TOKEN'),
)