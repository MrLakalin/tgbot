import json
import asyncio
import re
from datetime import datetime
from calendar import monthcalendar
from aiogram import types, Router, F
from aiogram.filters import Command
from typing import Dict, Any
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

router = Router()
user_tasks: Dict[str, Dict[str, asyncio.Task]] = {}
waiting_for: Dict[int, Any] = {}
reminders_file = 'reminders.json'
file_lock = asyncio.Lock()

REMINDER_EMOJI = {
    'default': '⏰',
    'birthday': '🎂',
    'meeting': '👥',
    'holiday': '🎉',
    'task': '📝'
}

REMINDER_TYPES = [
    ('Обычное', 'default'),
    ('День рождения', 'birthday'),
    ('Встреча', 'meeting'),
    ('Праздник', 'holiday'),
    ('Задача', 'task')
]

def create_time_keyboard() -> types.InlineKeyboardMarkup:
    keyboard = []
    for hour in range(0, 24, 3):
        row = []
        for h in range(hour, min(hour + 3, 24)):
            row.append(types.InlineKeyboardButton(
                text=f"{h:02d}:00",
                callback_data=f"time_{h:02d}_00"
            ))
        keyboard.append(row)
    
    keyboard.append([
        types.InlineKeyboardButton(
            text="« Назад к календарю",
            callback_data="back_to_calendar"
        )
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

def create_minutes_keyboard(hour: str) -> types.InlineKeyboardMarkup:
    keyboard = []
    for i in range(0, 60, 15):
        row = []
        for j in range(0, 3):
            minute = i + (j * 5)
            if minute < 60:
                row.append(types.InlineKeyboardButton(
                    text=f"{hour}:{minute:02d}",
                    callback_data=f"full_time_{hour}_{minute:02d}"
                ))
        keyboard.append(row)
    
    keyboard.append([
        types.InlineKeyboardButton(
            text="« Назад к выбору часа",
            callback_data="back_to_hours"
        )
    ])
    keyboard.append([
        types.InlineKeyboardButton(
            text="« Назад к календарю",
            callback_data="back_to_calendar"
        )
    ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

def create_year_month_keyboard(current_year: int) -> types.InlineKeyboardMarkup:
    keyboard = []
    month_names = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 
                   'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    
    keyboard.append([
        types.InlineKeyboardButton(text='⬅️', callback_data=f'prev_year_{current_year}'),
        types.InlineKeyboardButton(text=f"📅 {current_year}", callback_data='ignore'),
        types.InlineKeyboardButton(text='➡️', callback_data=f'next_year_{current_year}')
    ])
    
    for i in range(0, 12, 3):
        row = []
        for j in range(3):
            if i + j < 12:
                month_num = i + j + 1
                row.append(types.InlineKeyboardButton(
                    text=month_names[i + j],
                    callback_data=f'select_month_{current_year}_{month_num}'
                ))
        keyboard.append(row)
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

def create_calendar_keyboard(year: int, month: int) -> types.InlineKeyboardMarkup:
    keyboard = []
    month_names = [
        'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ]
    
    keyboard.append([
        types.InlineKeyboardButton(
            text=f"📅 {month_names[month-1]} {year}",
            callback_data=f'show_months_{year}'
        )
    ])
    
    days_of_week = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    keyboard.append([
        types.InlineKeyboardButton(text=day, callback_data='ignore')
        for day in days_of_week
    ])
    
    month_calendar = monthcalendar(year, month)
    
    for week in month_calendar:
        row = []
        for day in week:
            if day == 0:
                row.append(types.InlineKeyboardButton(text=' ', callback_data='ignore'))
            else:
                row.append(types.InlineKeyboardButton(
                    text=str(day),
                    callback_data=f'calendar_day_{year}_{month}_{day}'
                ))
        keyboard.append(row)
    
    nav_row = []
    
    prev_month = month - 1
    prev_year = year
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1
    
    next_month = month + 1
    next_year = year
    if next_month == 13:
        next_month = 1
        next_year += 1
    
    nav_row.extend([
        types.InlineKeyboardButton(
            text='⬅️',
            callback_data=f'prev_{prev_year}_{prev_month}'
        ),
        types.InlineKeyboardButton(
            text='➡️',
            callback_data=f'next_{next_year}_{next_month}'
        )
    ])
    keyboard.append(nav_row)
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

def create_reminders_keyboard(user_id: str, action: str) -> types.InlineKeyboardMarkup:
    keyboard = []
    user_reminders = reminders.get(user_id, [])
    
    for rem in user_reminders:
        text = rem['text'][:30] + '...' if len(rem['text']) > 30 else rem['text']
        keyboard.append([
            types.InlineKeyboardButton(
                text=f"🕐 {rem['time']} - {text}",
                callback_data=f"{action}_{rem['id']}"
            )
        ])
    
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

def create_reminder_type_keyboard() -> types.InlineKeyboardMarkup:
    keyboard = []
    for name, callback in REMINDER_TYPES:
        keyboard.append([
            types.InlineKeyboardButton(
                text=f"{REMINDER_EMOJI[callback]} {name}",
                callback_data=f"type_{callback}"
            )
        ])
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

def create_reminder_object(time: str, text: str, rem_type: str = 'default') -> dict:
    return {
        'time': time,
        'text': text,
        'type': rem_type,
        'id': str(datetime.now().timestamp())
    }

def load_reminders() -> Dict[str, list]:
    try:
        with open(reminders_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

async def save_reminders(data: Dict[str, list]) -> None:
    async with file_lock:
        try:
            with open(reminders_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving reminders to file: {e}")

reminders = load_reminders()

main = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Установить напоминание")],
        [KeyboardButton(text="Мои напоминания")],
        [KeyboardButton(text="Изменить напоминание"), KeyboardButton(text="Удалить напоминание")],
    ],
    resize_keyboard=True,
    input_field_placeholder='Выберите пункт меню...'
)

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    keyboard = [
        [
            types.KeyboardButton(text="Установить напоминание")
        ],
        [
            types.KeyboardButton(text="Мои напоминания")
        ],
        [
            types.KeyboardButton(text="Изменить напоминание"),
            types.KeyboardButton(text="Удалить напоминания")
        ]
    ]
    
    markup = types.ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )
    
    await message.answer(
        "Привет! Я бот напоминаний. 🤖\n"
        "Нужна помощь? Используйте /help для получения подробных инструкций.",
        reply_markup=markup
    )

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "❓ Добро пожаловать в справочник бота!\n\n"
        "<b>Основные команды:</b>\n"
        "• /start - Запустить бота\n"
        "• /help - Показать это сообщение\n\n"
        "<b>Типы напоминаний:</b>\n"
        f"• {REMINDER_EMOJI['default']} Обычное - повседневные дела\n"
        f"• {REMINDER_EMOJI['birthday']} День рождения - праздники друзей\n"
        f"• {REMINDER_EMOJI['meeting']} Встреча - деловые встречи\n"
        f"• {REMINDER_EMOJI['holiday']} Праздник - особые события\n"
        f"• {REMINDER_EMOJI['task']} Задача - важные дела\n\n"
        "<b>Как установить напоминание:</b>\n"
        "1. Нажмите \"Установить напоминание\"\n"
        "2. Выберите тип напоминания\n"
        "3. Укажите дату в календаре\n"
        "4. Выберите время с помощью кнопок\n"
        "5. Введите текст напоминания\n\n"
        "<b>Управление напоминаниями:</b>\n"
        "• 📋 \"Мои напоминания\" - список всех напоминаний\n"
        "• ✏️ \"Изменить напоминание\" - редактирование\n"
        "• 🗑 \"Удалить напоминание\" - удаление\n\n"
        "💡 Совет дня: Используйте разные типы напоминаний для лучшей организации задач."
    )
    
    await message.answer(help_text, parse_mode="HTML")

@router.message(F.text == "Установить напоминание")
async def set_reminder_start(message: types.Message):
    user_id = message.from_user.id
    waiting_for[user_id] = 'select_type'
    await message.answer(
        'Выберите тип напоминания:',
        reply_markup=create_reminder_type_keyboard()
    )

@router.callback_query(lambda c: c.data.startswith('edit_'))
async def process_edit_reminder(callback_query: types.CallbackQuery):
    _, rem_id = callback_query.data.split('_')
    user_id = str(callback_query.from_user.id)
    
    if user_id not in reminders:
        await callback_query.answer("❌ У вас нет напоминаний")
        return
    
    reminder = next((rem for rem in reminders[user_id] if rem['id'] == rem_id), None)
    if not reminder:
        await callback_query.answer("❌ Напоминание не найдено")
        return
    
    now = datetime.now()
    waiting_for[int(user_id)] = 'edit_calendar'
    waiting_for[user_id + '_edit_id'] = rem_id
    waiting_for[user_id + '_edit_type'] = reminder['type']
    waiting_for[user_id + '_edit_old_reminder'] = reminder
    
    calendar_keyboard = create_calendar_keyboard(now.year, now.month)
    
    await callback_query.message.edit_text(
        "📅 Выберите новую дату напоминания:",
        reply_markup=calendar_keyboard
    )

@router.callback_query(lambda c: c.data == "back_to_reminders")
async def process_back_to_reminders(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    
    waiting_for.pop(int(user_id), None)
    waiting_for.pop(user_id + '_edit_id', None)
    waiting_for.pop(user_id + '_edit_type', None)
    waiting_for.pop(user_id + '_edit_old_reminder', None)
    
    user_reminders = reminders.get(user_id, [])
    
    if not user_reminders:
        await callback_query.message.edit_text("📭 У вас нет активных напоминаний")
        return

    response = "📋 <b>Ваши напоминания</b>\n\n"
    
    grouped_by_date = {}
    for rem in user_reminders:
        date = rem['time'].split()[0]
        if date not in grouped_by_date:
            grouped_by_date[date] = []
        grouped_by_date[date].append(rem)

    sorted_dates = sorted(grouped_by_date.keys(), 
                         key=lambda x: datetime.strptime(x, "%d.%m.%Y"))

    total_count = len(user_reminders)
    response += f"Всего напоминаний: {total_count}\n\n"

    keyboard = []
    for date in sorted_dates:
        formatted_date = datetime.strptime(date, "%d.%m.%Y").strftime("%d %B %Y")
        month_translations = {
            'January': 'января', 'February': 'февраля', 'March': 'марта',
            'April': 'апреля', 'May': 'мая', 'June': 'июня',
            'July': 'июля', 'August': 'августа', 'September': 'сентября',
            'October': 'октября', 'November': 'ноября', 'December': 'декабря'
        }
        for eng, rus in month_translations.items():
            formatted_date = formatted_date.replace(eng, rus)
        
        response += f"📅 <b>{formatted_date}</b>\n"
        
        day_reminders = sorted(grouped_by_date[date], 
                             key=lambda x: datetime.strptime(x['time'].split()[1], "%H:%M"))
        
        for rem in day_reminders:
            time = rem['time'].split()[1]
            rem_type = rem.get('type', 'default')
            emoji = REMINDER_EMOJI.get(rem_type, '⏰')
            
            type_name = next((name for name, callback in REMINDER_TYPES if callback == rem_type), 'Обычное')
            
            response += (
                f"┌ <b>{time}</b>\n"
                f"├ {emoji} <i>{type_name}</i>\n"
                f"└ {rem['text']}\n\n"
            )
            
            keyboard.append([
                types.InlineKeyboardButton(
                    text="✏️ Изменить",
                    callback_data=f"edit_{rem['id']}"
                ),
                types.InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=f"delete_{rem['id']}"
                )
            ])

    await callback_query.message.edit_text(
        response,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )

@router.callback_query(lambda c: c.data.startswith('calendar_day_'))
async def process_calendar_day(callback_query: types.CallbackQuery):
    _, _, year, month, day = callback_query.data.split('_')
    selected_date = f"{day.zfill(2)}.{month.zfill(2)}.{year}"
    user_id = str(callback_query.from_user.id)
    
    current_action = waiting_for.get(int(user_id))
    if current_action == 'edit_calendar':
        rem_type = waiting_for.get(user_id + '_edit_type', 'default')
    else:
        rem_type = current_action[1] if isinstance(current_action, tuple) else 'default'
    
    await callback_query.message.edit_text(
        f"Выбрана дата: {selected_date}\nВыберите час:",
        reply_markup=create_time_keyboard()
    )
    
    if current_action == 'edit_calendar':
        waiting_for[int(user_id)] = ('edit_time', selected_date, rem_type)
    else:
        waiting_for[int(user_id)] = ('set_time', selected_date, rem_type)

@router.callback_query(lambda c: c.data.startswith('time_'))
async def process_time_selection(callback_query: types.CallbackQuery):
    _, hour, _ = callback_query.data.split('_')
    user_id = callback_query.from_user.id
    current_action = waiting_for.get(user_id)
    
    if current_action and isinstance(current_action, tuple):
        date_str = current_action[1]
        rem_type = current_action[2] if len(current_action) > 2 else 'default'
        waiting_for[user_id] = ('set_time', date_str, rem_type)
        
    await callback_query.message.edit_reply_markup(
        reply_markup=create_minutes_keyboard(hour)
    )

@router.callback_query(lambda c: c.data == 'back_to_hours')
async def process_back_to_hours(callback_query: types.CallbackQuery):
    await callback_query.message.edit_reply_markup(
        reply_markup=create_time_keyboard()
    )

@router.callback_query(lambda c: c.data.startswith('full_time_'))
async def process_full_time_selection(callback_query: types.CallbackQuery):
    parts = callback_query.data.split('_')
    hour = parts[2]
    minutes = parts[3]
    time_str = f"{hour}:{minutes}"
    user_id = callback_query.from_user.id
    action = waiting_for.get(user_id)
    
    if not action or not isinstance(action, tuple):
        await callback_query.answer("Ошибка: начните процесс заново")
        return
    
    date_str = action[1]
    rem_type = action[2] if len(action) > 2 else 'default'
    
    reminder_time = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
    if reminder_time < datetime.now():
        await callback_query.answer("❌ Нельзя установить напоминание в прошлом!")
        return
    
    type_name = next((name for name, callback in REMINDER_TYPES if callback == rem_type), 'Обычное')
    await callback_query.message.edit_text(
        f"Выбраны дата и время: {date_str} {time_str}\n"
        f"Тип: {type_name} {REMINDER_EMOJI[rem_type]}\n"
        f"Теперь введите текст напоминания:"
    )
    waiting_for[user_id] = ('set_reminder_text', date_str, time_str, rem_type)

@router.callback_query(lambda c: c.data.startswith('type_'))
async def process_reminder_type(callback_query: types.CallbackQuery):
    rem_type = callback_query.data.split('_')[1]
    user_id = callback_query.from_user.id
    now = datetime.now()
    
    waiting_for[user_id] = ('calendar', rem_type)
    await callback_query.message.edit_text(
        'Выберите дату:',
        reply_markup=create_calendar_keyboard(now.year, now.month)
    )

@router.message(F.text == 'Мои напоминания')
async def show_reminders(message: types.Message):
    user_id = str(message.from_user.id)
    user_reminders = reminders.get(user_id, [])
    
    if not user_reminders:
        await message.answer("📭 У вас нет активных напоминаний")
        return

    grouped_by_date = {}
    for rem in user_reminders:
        date = rem['time'].split()[0]
        if date not in grouped_by_date:
            grouped_by_date[date] = []
        grouped_by_date[date].append(rem)

    sorted_dates = sorted(grouped_by_date.keys(), 
                         key=lambda x: datetime.strptime(x, "%d.%m.%Y"))

    response = "📋 <b>Ваши напоминания</b>\n\n"
    
    total_count = len(user_reminders)
    response += f"Всего напоминаний: {total_count}\n\n"

    for date in sorted_dates:
        formatted_date = datetime.strptime(date, "%d.%m.%Y").strftime("%d %B %Y")
        month_translations = {
            'January': 'января', 'February': 'февраля', 'March': 'марта',
            'April': 'апреля', 'May': 'мая', 'June': 'июня',
            'July': 'июля', 'August': 'августа', 'September': 'сентября',
            'October': 'октября', 'November': 'ноября', 'December': 'декабря'
        }
        for eng, rus in month_translations.items():
            formatted_date = formatted_date.replace(eng, rus)
        
        response += f"📅 <b>{formatted_date}</b>\n"
        
        day_reminders = sorted(grouped_by_date[date], 
                             key=lambda x: datetime.strptime(x['time'].split()[1], "%H:%M"))
        
        for rem in day_reminders:
            time = rem['time'].split()[1]
            rem_type = rem.get('type', 'default')
            emoji = REMINDER_EMOJI.get(rem_type, '⏰')
            
            type_name = next((name for name, callback in REMINDER_TYPES if callback == rem_type), 'Обычное')
            
            response += (
                f"┌ <b>{time}</b>\n"
                f"├ {emoji} <i>{type_name}</i>\n"
                f"└ {rem['text']}\n\n"
            )

    try:
        response += (
            "\n<i>💡 Управление напоминаниями:</i>\n"
            "• Изменить напоминание - нажмите соответствующую кнопку\n"
            "• Удалить напоминание - используйте кнопку удаления"
        )
        
        await message.answer(response, parse_mode="HTML")
    except Exception as e:
        print(f"Error sending reminders: {e}")
        await message.answer(
            "⚠️ Не удалось отобразить полный список напоминаний.\n"
            "Попробуйте удалить несколько старых напоминаний."
        )

@router.message(F.text == "Удалить напоминания")
async def show_delete_reminders(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in reminders or not reminders[user_id]:
        await message.answer("📭 У вас нет активных напоминаний")
        return

    keyboard = []
    
    sorted_reminders = sorted(reminders[user_id], 
                            key=lambda x: datetime.strptime(x['time'], "%d.%m.%Y %H:%M"))
    
    for rem in sorted_reminders:
        date_time = rem['time']
        text = rem['text']
        rem_type = rem.get('type', 'default')
        emoji = REMINDER_EMOJI.get(rem_type, '⏰')
        
        display_text = text[:30] + ('...' if len(text) > 30 else '')
        
        keyboard.append([
            types.InlineKeyboardButton(
                text=f"☐ {date_time} {emoji} {display_text}",
                callback_data=f"select_del_{rem['id']}"
            )
        ])
    
    control_buttons = [
        [
            types.InlineKeyboardButton(text="✅ Выбрать все", callback_data="select_all_del"),
            types.InlineKeyboardButton(text="❌ Отменить все", callback_data="deselect_all_del")
        ],
        [
            types.InlineKeyboardButton(text="🗑 Удалить выбранные", callback_data="confirm_delete")
        ]
    ]
    keyboard.extend(control_buttons)
    
    markup = types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    await message.answer(
        "🗑 <b>Множественное удаление напоминаний</b>\n\n"
        "<i>Инструкция:</i>\n"
        "1️⃣ Нажмите на ☐ рядом с напоминанием, чтобы выбрать его\n"
        "2️⃣ Выберите одно или несколько напоминаний\n"
        "3️⃣ Используйте кнопки внизу для быстрого выбора\n"
        "4️⃣ Нажмите «🗑 Удалить выбранные» для подтверждения\n\n"
        "<i>❗️ Удаление необратимо</i>",
        reply_markup=markup,
        parse_mode="HTML"
    )

@router.callback_query(lambda c: c.data.startswith('select_del_'))
async def process_select_reminder(callback_query: types.CallbackQuery):
    keyboard = list(callback_query.message.reply_markup.inline_keyboard)
    
    for row_index, row in enumerate(keyboard):
        for btn_index, btn in enumerate(row):
            if btn.callback_data == callback_query.data:
                current_text = btn.text
                new_text = current_text.replace('☐', '☑') if '☐' in current_text else current_text.replace('☑', '☐')
                keyboard[row_index][btn_index] = types.InlineKeyboardButton(
                    text=new_text,
                    callback_data=btn.callback_data
                )
                break
    
    await callback_query.message.edit_reply_markup(
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(lambda c: c.data == "select_all_del")
async def process_select_all(callback_query: types.CallbackQuery):
    keyboard = list(callback_query.message.reply_markup.inline_keyboard)
    modified = False
    
    for row_index, row in enumerate(keyboard):
        for btn_index, btn in enumerate(row):
            if btn.callback_data.startswith('select_del_'):
                current_text = btn.text
                if '☐' in current_text:
                    modified = True
                    new_text = current_text.replace('☐', '☑')
                    keyboard[row_index][btn_index] = types.InlineKeyboardButton(
                        text=new_text,
                        callback_data=btn.callback_data
                    )
    
    if modified:
        await callback_query.message.edit_reply_markup(
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    else:
        await callback_query.answer("Все напоминания уже выбраны")

@router.callback_query(lambda c: c.data == "deselect_all_del")
async def process_deselect_all(callback_query: types.CallbackQuery):
    keyboard = list(callback_query.message.reply_markup.inline_keyboard)
    modified = False
    
    for row_index, row in enumerate(keyboard):
        for btn_index, btn in enumerate(row):
            if btn.callback_data.startswith('select_del_'):
                current_text = btn.text
                if '☑' in current_text:
                    modified = True
                    new_text = current_text.replace('☑', '☐')
                    keyboard[row_index][btn_index] = types.InlineKeyboardButton(
                        text=new_text,
                        callback_data=btn.callback_data
                    )
    
    if modified:
        await callback_query.message.edit_reply_markup(
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    else:
        await callback_query.answer("Все напоминания уже сняты")

@router.callback_query(lambda c: c.data == "confirm_delete")
async def process_confirm_delete(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    keyboard = callback_query.message.reply_markup.inline_keyboard
    
    selected_ids = []
    for row in keyboard:
        for btn in row:
            if btn.callback_data.startswith('select_del_') and '☑' in btn.text:
                rem_id = btn.callback_data.split('_')[2]
                selected_ids.append(rem_id)
    
    if not selected_ids:
        await callback_query.answer("❌ Не выбрано ни одного напоминания")
        return
    
    deleted_count = 0
    if user_id in reminders:
        new_reminders = []
        for rem in reminders[user_id]:
            if rem['id'] in selected_ids:
                if user_id in user_tasks and rem['text'] in user_tasks[user_id]:
                    user_tasks[user_id][rem['text']].cancel()
                    del user_tasks[user_id][rem['text']]
                deleted_count += 1
            else:
                new_reminders.append(rem)
        
        if new_reminders:
            reminders[user_id] = new_reminders
        else:
            del reminders[user_id]
        
        await save_reminders(reminders)
    
    await callback_query.message.edit_text(
        f"✅ Успешно удалено напоминаний: {deleted_count}\n\n"
        f"<i>Используйте команду «Мои напоминания» для просмотра оставшихся напоминаний</i>",
        parse_mode="HTML"
    )

@router.message(F.text == "Изменить напоминание")
async def edit_reminder_start(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in reminders or not reminders[user_id]:
        await message.answer("📭 У вас нет активных напоминаний")
        return
    
    keyboard = []
    
    sorted_reminders = sorted(reminders[user_id], 
                            key=lambda x: datetime.strptime(x['time'], "%d.%m.%Y %H:%M"))
    
    for rem in sorted_reminders:
        time = rem['time']
        rem_type = rem.get('type', 'default')
        emoji = REMINDER_EMOJI.get(rem_type, '⏰')
        
        keyboard.append([
            types.InlineKeyboardButton(
                text=f"✏️ {time} {emoji} {rem['text'][:20]}{'...' if len(rem['text']) > 20 else ''}",
                callback_data=f"edit_{rem['id']}"
            )
        ])

    await message.answer(
        "Выберите напоминание для изменения:",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )

@router.callback_query(lambda c: c.data.startswith(('delete_', 'edit_')))
async def process_reminder_action(callback_query: types.CallbackQuery):
    action, rem_id = callback_query.data.split('_')
    user_id = str(callback_query.from_user.id)
    
    if user_id not in reminders:
        await callback_query.answer("❌ У вас нет напоминаний")
        return
    
    reminder = next((rem for rem in reminders[user_id] if rem['id'] == rem_id), None)
    if not reminder:
        await callback_query.answer("❌ Напоминание не найдено")
        return
    
    if action == 'delete':
        if user_id in user_tasks and reminder['text'] in user_tasks[user_id]:
            user_tasks[user_id][reminder['text']].cancel()
            del user_tasks[user_id][reminder['text']]
        
        reminders[user_id] = [rem for rem in reminders[user_id] if rem['id'] != rem_id]
        if not reminders[user_id]:
            del reminders[user_id]
        await save_reminders(reminders)
        await callback_query.message.edit_text("✅ Напоминание удалено")
        
    else:  # edit
        now = datetime.now()
        waiting_for[int(user_id)] = 'edit_calendar'
        waiting_for[user_id + '_edit_id'] = rem_id
        await callback_query.message.edit_text(
            'Выберите новую дату:',
            reply_markup=create_calendar_keyboard(now.year, now.month)
        )
    
    await callback_query.answer()

@router.callback_query(lambda c: c.data == 'ignore')
async def process_ignore(callback_query: types.CallbackQuery):
    await callback_query.answer()

@router.callback_query(lambda c: c.data.startswith('show_months_'))
async def process_show_months(callback_query: types.CallbackQuery):
    try:
        _, _, year = callback_query.data.split('_')
        current_year = int(year)
        new_markup = create_year_month_keyboard(current_year)
        
        if callback_query.message.reply_markup != new_markup:
            await callback_query.message.edit_reply_markup(reply_markup=new_markup)
        else:
            await callback_query.answer()
            
    except Exception as e:
        print(f"Error in show months: {e}")
        await callback_query.answer("Ошибка при отображении месяцев")

@router.callback_query(lambda c: c.data.startswith(('prev_year_', 'next_year_')))
async def process_year_navigation(callback_query: types.CallbackQuery):
    try:
        _, _, year = callback_query.data.split('_')
        year = int(year)
        
        if callback_query.data.startswith('prev_year_'):
            new_year = year - 1
        else:  # next_year_
            new_year = year + 1
        
        if new_year != year:
            await callback_query.message.edit_reply_markup(
                reply_markup=create_year_month_keyboard(new_year)
            )
        else:
            await callback_query.answer()
            
    except Exception as e:
        print(f"Error in year navigation: {e}")
        await callback_query.answer("Ошибка при навигации")

@router.callback_query(lambda c: c.data.startswith('select_month_'))
async def process_month_selection(callback_query: types.CallbackQuery):
    try:
        _, _, year, month = callback_query.data.split('_')
        year, month = int(year), int(month)
        
        new_markup = create_calendar_keyboard(year, month)
        
        if callback_query.message.reply_markup != new_markup:
            await callback_query.message.edit_reply_markup(reply_markup=new_markup)
        else:
            await callback_query.answer()
            
    except Exception as e:
        print(f"Error in month selection: {e}")
        await callback_query.answer("Ошибка при выборе месяца")

@router.callback_query(lambda c: c.data.startswith(('prev_', 'next_')))
async def process_calendar_navigation(callback_query: types.CallbackQuery):
    try:
        action, year, month = callback_query.data.split('_')
        year, month = int(year), int(month)
        
        new_markup = create_calendar_keyboard(year, month)
        
        await callback_query.message.edit_reply_markup(reply_markup=new_markup)
            
    except Exception as e:
        print(f"Error in calendar navigation: {e}")
        await callback_query.answer("Ошибка при навигации по календарю")

@router.message(F.text)
async def handle_text(message: types.Message):
    if message.text.startswith('/'):
        return
        
    user_id = message.from_user.id
    action = waiting_for.get(user_id)
    
    if not action or not isinstance(action, tuple):
        return

    if action[0] == 'set_reminder_text':
        date_str, time_str, rem_type = action[1:4]
        text = message.text
        
        reminder_time = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
        success = await schedule_reminder(message.bot, user_id, reminder_time, text, rem_type)
        
        if not success:
            await message.answer("❌ Не удалось установить напоминание")
        
        waiting_for.pop(user_id, None)
        waiting_for.pop(str(user_id) + '_edit_id', None)
        waiting_for.pop(str(user_id) + '_edit_type', None)

async def send_reminder(bot, user_id: int, text: str):
    try:
        user_id_str = str(user_id)
        reminder = next((rem for rem in reminders[user_id_str] if rem['text'] == text), None)
        
        if reminder:
            type_name = next((name for name, callback in REMINDER_TYPES if callback == reminder['type']), 'Обычное')
            emoji = REMINDER_EMOJI[reminder['type']]
            
            reminder_message = (
                f"🔔 <b>Напоминание!</b>\n\n"
                f"{emoji} <b>Тип:</b> {type_name}\n"
                f"📝 <b>Сообщение:</b> {text}\n\n"
                f"<i>Установлено на: {reminder['time']}</i>"
            )
            
            await bot.send_message(user_id, reminder_message, parse_mode="HTML")
    except Exception as e:
        print(f"Error in send_reminder: {e}")
        await bot.send_message(user_id, f"⏰ Напоминание: {text}")

async def schedule_reminder(bot, user_id: int, reminder_time: datetime, text: str, rem_type: str = 'default') -> bool:
    try:
        if reminder_time < datetime.now():
            await bot.send_message(user_id, "❌ Нельзя установить напоминание в прошлом!")
            return False

        user_id_str = str(user_id)
        
        old_reminder = waiting_for.get(user_id_str + '_edit_old_reminder')
        
        if old_reminder:
            if user_id_str in reminders:
                reminders[user_id_str] = [rem for rem in reminders[user_id_str] if rem['id'] != old_reminder['id']]
            if user_id_str in user_tasks and old_reminder['text'] in user_tasks[user_id_str]:
                user_tasks[user_id_str][old_reminder['text']].cancel()
                del user_tasks[user_id_str][old_reminder['text']]
        
        delta = (reminder_time - datetime.now()).total_seconds()
        task = asyncio.create_task(reminder_task(bot, user_id, delta, text))

        if user_id_str not in user_tasks:
            user_tasks[user_id_str] = {}
        user_tasks[user_id_str][text] = task
        
        if user_id_str not in reminders:
            reminders[user_id_str] = []
        
        reminder_obj = create_reminder_object(
            time=reminder_time.strftime("%d.%m.%Y %H:%M"),
            text=text,
            rem_type=rem_type
        )
        
        reminders[user_id_str].append(reminder_obj)
        await save_reminders(reminders)

        waiting_for.pop(user_id_str + '_edit_old_reminder', None)
        
        type_name = next((name for name, callback in REMINDER_TYPES if callback == rem_type), 'Обычное')
        formatted_date = reminder_time.strftime("%d %B %Y")
        month_translations = {
            'January': 'января', 'February': 'февраля', 'March': 'марта',
            'April': 'апреля', 'May': 'мая', 'June': 'июня',
            'July': 'июля', 'August': 'августа', 'September': 'сентября',
            'October': 'октября', 'November': 'ноября', 'December': 'декабря'
        }
        for eng, rus in month_translations.items():
            formatted_date = formatted_date.replace(eng, rus)

        action_text = "изменено" if old_reminder else "создано"
        confirmation_message = (
            f"✅ Напоминание {action_text}\n\n"
            f"📅 <b>Дата:</b> {formatted_date}\n"
            f"⏰ <b>Время:</b> {reminder_time.strftime('%H:%M')}\n"
            f"{REMINDER_EMOJI[rem_type]} <b>Тип:</b> {type_name}\n"
            f"📝 <b>Текст:</b> {text}\n\n"
            f"<i>Я напомню вам об этом {formatted_date} в {reminder_time.strftime('%H:%M')}</i>"
        )
        
        await bot.send_message(user_id, confirmation_message, parse_mode="HTML")
        return True
        
    except Exception as e:
        print(f"Error in schedule_reminder: {e}")
        return False

async def reminder_task(bot, user_id: int, delay: float, text: str):
    try:
        await asyncio.sleep(delay)
        await send_reminder(bot, user_id, text)
        
        user_id_str = str(user_id)
        if user_id_str in reminders:
            reminders[user_id_str] = [rem for rem in reminders[user_id_str] if rem['text'] != text]
            if not reminders[user_id_str]:
                del reminders[user_id_str]
            await save_reminders(reminders)

        if user_id_str in user_tasks and text in user_tasks[user_id_str]:
            del user_tasks[user_id_str][text]
            
    except Exception as e:
        print(f"Error in reminder_task: {e}")

async def edit_reminder(bot, user_id: int, rem_id: int, new_time: datetime, new_text: str):
    user_id_str = str(user_id)
    if user_id_str not in reminders:
        await bot.send_message(user_id, "❌ У вас нет напоминаний")
        return

    reminder_to_edit = next((rem for rem in reminders[user_id_str] if rem['id'] == rem_id), None)
    if not reminder_to_edit:
        await bot.send_message(user_id, "❌ Напоминание не найдено")
        return

    if user_id_str in user_tasks and reminder_to_edit['text'] in user_tasks[user_id_str]:
        user_tasks[user_id_str][reminder_to_edit['text']].cancel()
        del user_tasks[user_id_str][reminder_to_edit['text']]

    reminders[user_id_str] = [rem for rem in reminders[user_id_str] if rem['id'] != rem_id]

    if await schedule_reminder(bot, user_id, new_time, new_text):
        await save_reminders(reminders)
        await bot.send_message(user_id, f"✅ Напоминание обновлено на {new_time.strftime('%d.%m.%Y %H:%M')}")
    else:
        await bot.send_message(user_id, "❌ Не удалось обновить напоминание")

@router.message(lambda message: message.text == "Установить напоминание")
async def set_reminder_start(message: types.Message):
    try:
        user_id = message.from_user.id
        now = datetime.now()
        waiting_for[user_id] = ('calendar', 'default')
        
        keyboard = create_calendar_keyboard(now.year, now.month)
        
        await message.answer(
            'Выберите дату:',
            reply_markup=keyboard
        )
        
    except Exception as e:
        print(f"Error in set_reminder_start: {e}")
        await message.answer("Произошла ошибка при запуске установки напоминания")

@router.callback_query(lambda c: c.data == "back_to_calendar")
async def process_back_to_calendar(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    now = datetime.now()
    current_action = waiting_for.get(user_id)
    
    is_editing = isinstance(current_action, tuple) and current_action[0] in ['edit_time', 'set_time']
    
    if is_editing:
        rem_type = current_action[2] if len(current_action) > 2 else 'default'
        if len(current_action) > 3:
            waiting_for[str(user_id) + '_edit_id'] = current_action[3]
            waiting_for[user_id] = 'edit_calendar'
        else:
            waiting_for[user_id] = ('calendar', rem_type)
    else:
        waiting_for[user_id] = ('calendar', 'default')
    
    await callback_query.message.edit_text(
        'Выберите дату:',
        reply_markup=create_calendar_keyboard(now.year, now.month)
    )

@router.callback_query(lambda c: c.data == 'ignore')
async def process_ignore(callback_query: types.CallbackQuery):
    await callback_query.answer()
