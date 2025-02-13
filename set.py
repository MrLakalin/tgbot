import json
import asyncio
import re
from datetime import datetime
from aiogram import types, Router, F
from aiogram.filters import Command

import keyboard as kb

router = Router()
user_tasks = {}
waiting_for = {}
reminders_file = 'reminders.json'
file_lock = asyncio.Lock()


def load_reminders():
    try:
        with open(reminders_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_reminders(data):
    async def _save():
        async with file_lock:
            try:
                with open(reminders_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                print("Напоминания успешно сохранены")
            except Exception as e:
                print(f"Ошибка при сохранении напоминаний: {e}")

    print("Запускаю сохранение напоминаний...")
    asyncio.create_task(_save())


reminders = load_reminders()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer('Привет! Я бот напоминаний.', reply_markup=kb.main)


async def send_reminder(bot, user_id, text):
    await bot.send_message(user_id, f"⏰ Напоминание: {text}")


async def schedule_reminder(bot, user_id, reminder_time, text):
    now = datetime.now()
    if reminder_time < now:
        await bot.send_message(user_id, "❌ Нельзя установить напоминание в прошлом!")
        return False

    delta = (reminder_time - now).total_seconds()
    task = asyncio.create_task(reminder_task(bot, user_id, delta, text))

    user_id_str = str(user_id)
    if user_id_str not in user_tasks:
        user_tasks[user_id_str] = {}
    user_tasks[user_id_str][text] = task

    reminders.setdefault(user_id_str, []).append({
        'time': reminder_time.strftime("%d.%m.%Y %H:%M"),
        'text': text,
        'id': len(reminders.get(user_id_str, [])) + 1
    })
    return True


async def reminder_task(bot, user_id, delay, text):
    await asyncio.sleep(delay)
    try:
        await send_reminder(bot, user_id, text)

        user_id_str = str(user_id)
        if user_id_str in reminders:
            reminders[user_id_str] = [rem for rem in reminders[user_id_str] if rem['text'] != text]
            if not reminders[user_id_str]:
                del reminders[user_id_str]
            save_reminders(reminders)

        if user_id_str in user_tasks and text in user_tasks[user_id_str]:
            del user_tasks[user_id_str][text]
    except Exception as e:
        print(f"Ошибка при выполнении напоминания: {e}")


async def edit_reminder(bot, user_id, rem_id, new_time, new_text):
    user_id_str = str(user_id)
    if user_id_str not in reminders:
        await bot.send_message(user_id, "❌ У вас нет напоминаний")
        return

    reminder_to_edit = None
    for rem in reminders[user_id_str]:
        if rem['id'] == rem_id:
            reminder_to_edit = rem
            break

    if not reminder_to_edit:
        await bot.send_message(user_id, "❌ Напоминание не найдено")
        return

    if user_id_str in user_tasks and reminder_to_edit['text'] in user_tasks[user_id_str]:
        task = user_tasks[user_id_str][reminder_to_edit['text']]
        task.cancel()
        del user_tasks[user_id_str][reminder_to_edit['text']]

    reminders[user_id_str] = [rem for rem in reminders[user_id_str] if rem['id'] != rem_id]

    success = await schedule_reminder(bot, user_id, new_time, new_text)
    if success:
        save_reminders(reminders)
        await bot.send_message(user_id, f"✅ Напоминание обновлено на {new_time.strftime('%d.%m.%Y %H:%M')}")
    else:
        await bot.send_message(user_id, "❌ Не удалось обновить напоминание")

@router.message(F.text == 'Установить напоминание')
async def set_reminder(message: types.Message):
    user_id = message.from_user.id
    waiting_for[user_id] = 'set'
    await message.answer('Введите дату, время и текст в формате: ДД.ММ.ГГГГ ЧЧ:MM Текст')


@router.message(F.text == 'Мои напоминания')
async def show_reminders(message: types.Message):
    user_id = str(message.from_user.id)
    user_reminders = reminders.get(user_id, [])
    if not user_reminders:
        await message.answer("У вас нет активных напоминаний")
        return

    response = "Ваши напоминания:\n"
    for rem in user_reminders:
        response += f"{rem['id']}. {rem['time']} - {rem['text']}\n"
    await message.answer(response)


@router.message(F.text == 'Удалить напоминание')
async def delete_reminder_start(message: types.Message):
    user_id = message.from_user.id
    waiting_for[user_id] = 'delete'
    await message.answer("Введите ID напоминания для удаления:")


@router.message(F.text == 'Изменить напоминание')
async def edit_reminder_start(message: types.Message):
    user_id = message.from_user.id
    waiting_for[user_id] = 'edit'
    await message.answer("Введите ID напоминания, новое время и текст в формате: ID ДД.ММ.ГГГГ ЧЧ:MM Новый_текст")


@router.message(F.text)
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    action = waiting_for.get(user_id)

    if not action:
        return

    try:
        if action == 'set':
            match = re.match(r"(\d{2}.\d{2}.\d{4})\s+(\d{2}:\d{2})\s+(.+)", message.text)
            if not match:
                raise ValueError("Неверный формат даты или времени")

            date_str, time_str, text = match.groups()
            reminder_time = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
            if await schedule_reminder(message.bot, user_id, reminder_time, text):
                save_reminders(reminders)
                await message.answer(f"✅ Напоминание установлено на {reminder_time.strftime('%d.%m.%Y %H:%M')}")

        elif action == 'delete':
            rem_id = int(message.text)
            user_id_str = str(user_id)
            if user_id_str in reminders:
                reminder_to_delete = next((rem for rem in reminders[user_id_str] if rem['id'] == rem_id), None)
                if reminder_to_delete:
                    if user_id_str in user_tasks and reminder_to_delete['text'] in user_tasks[user_id_str]:
                        task = user_tasks[user_id_str][reminder_to_delete['text']]
                        task.cancel()
                        del user_tasks[user_id_str][reminder_to_delete['text']]

                    reminders[user_id_str] = [rem for rem in reminders[user_id_str] if rem['id'] != rem_id]
                    if not reminders[user_id_str]:
                        del reminders[user_id_str]
                    save_reminders(reminders)
                    await message.answer("✅ Напоминание удалено")
                else:
                    await message.answer("❌ Напоминание не найдено")
            else:
                await message.answer("❌ У вас нет напоминаний")

        elif action == 'edit':
            parts = message.text.split(' ', 3)
            if len(parts) < 4:
                raise ValueError("Неверный формат")

            rem_id = int(parts[0])
            date_str = parts[1]
            time_str = parts[2]
            new_text = parts[3]
            new_time = datetime.strptime(f"{date_str} {time_str}", "%d.%m.%Y %H:%M")
            user_id_str = str(user_id)

            await edit_reminder(message.bot, user_id, rem_id, new_time, new_text)

    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    finally:
        waiting_for.pop(user_id, None)