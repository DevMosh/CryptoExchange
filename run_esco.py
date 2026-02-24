import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import MenuButtonWebApp, WebAppInfo

from dotenv import load_dotenv

from database.connect import create_tables
from handlers.admins import setup_admin_routers
# from handlers.admins import setup_admin_routers
from handlers.users import setup_routers

load_dotenv()
bot = Bot(token=os.getenv('BOT_TOKEN'), default=DefaultBotProperties(parse_mode='html'))
dp = Dispatcher()


async def main():
    await create_tables()
    print("База данных подключена и проверена.")

    # await bot.set_chat_menu_button(
    #     menu_button=MenuButtonWebApp(
    #         text="QR-сканер",  # Текст, который будет на кнопке
    #         web_app=WebAppInfo(url='https://escotrust.ru/contacts')
    #     )
    # )

    router = setup_routers()
    admin_router = setup_admin_routers()
    # router_other = setup_routers_other()
    dp.include_routers(
        router,
        admin_router,
        # router_other
    )
    dp.startup.register(on_startup)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def on_startup(dispatcher: Dispatcher):
    # await async_main()
    ...

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Бот выключен')
