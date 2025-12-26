from aiogram import types
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def start_keyboard():
    builder = ReplyKeyboardBuilder()

    builder.row(
        types.KeyboardButton(text="Обмен 💱"),
    )
    builder.row(
        types.KeyboardButton(text="История 🗄"),
        types.KeyboardButton(text="Поддержка 📧")
    )

    return builder.as_markup(
        resize_keyboard=True,
        input_field_placeholder="Выберите действие:"
    )
