from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text='Установить напоминание')],
        [KeyboardButton(text='Мои напоминания')],
        [KeyboardButton(text='Удалить напоминание'), KeyboardButton(text='Изменить напоминание')]],
    resize_keyboard=True,
    input_field_placeholder='Выберите пункт меню...'
)