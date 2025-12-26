from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_buy_sell_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        types.InlineKeyboardButton(
            text="🛒 Купить",
            callback_data="action_buy"
        ),
        types.InlineKeyboardButton(
            text="💰 Продать",
            callback_data="action_sell"
        )
    )

    return builder.as_markup()


def confirm_buy():
    builder = InlineKeyboardBuilder()

    builder.row(
        types.InlineKeyboardButton(
            text="Да",
            callback_data="confirm_buy"
        )
    )

    return builder.as_markup()