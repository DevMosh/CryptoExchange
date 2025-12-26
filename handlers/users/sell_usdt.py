from aiogram import Router, F, types

router = Router()

@router.callback_query(F.data == "action_sell")
async def process_sell(callback: types.CallbackQuery):
    await callback.message.edit_text("Вы выбрали продажу USDT. Введите сумму:")