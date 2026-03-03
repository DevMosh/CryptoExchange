from aiogram import types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.config import terms


def get_buy_sell_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        types.InlineKeyboardButton(
            text="🛒 Купить",
            switch_inline_query_current_chat="buy "
        ),
        types.InlineKeyboardButton(
            text="💰 Продать",
            switch_inline_query_current_chat="sell "
        )
    )

    return builder.as_markup()


def confirm_buy():
    builder = InlineKeyboardBuilder()

    builder.row(
        types.InlineKeyboardButton(
            text="Оплатить",
            callback_data="confirm_buy_usdt"
        )
    )

    return builder.as_markup()


def get_payment_rules_keyboard():
    builder = InlineKeyboardBuilder()

    # Кнопка согласия
    # Нажатие на неё должно триггерить выдачу ссылки
    builder.row(
        types.InlineKeyboardButton(
            text="Да, соглашаюсь",
            callback_data="accept_rules_pay"
        )
    )

    # Кнопка отмены
    builder.row(
        types.InlineKeyboardButton(
            text="Отмена",
            callback_data="cancel_payment"
        )
    )

    return builder.as_markup()


def get_cancel_keyboard():
    builder = InlineKeyboardBuilder()

    builder.row(
        types.InlineKeyboardButton(
            text="Отмена",
            callback_data="cancel_payment"
        )
    )

    return builder.as_markup()


# --- Клавиатура для оферты ---
def get_terms_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принимаю условия", callback_data="accept_terms")],
        [InlineKeyboardButton(text="📄 Читать оферту", url=f"{terms}")] # Ссылка-пример
    ])


def history_type_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="🛒 Покупка", callback_data="history_buy"),
            InlineKeyboardButton(text="💸 Продажа", callback_data="history_sell")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)