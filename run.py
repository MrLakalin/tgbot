import asyncio
import re
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command

from config import TOKEN

router = Router()

user_tasks = {}

async def send_reminder(bot, user_id, text):
    await bot.send_message(user_id, f"⏰ Напоминание: {text}")

async def schedule_reminder(bot, user_id, time_str, text):
    try:
        now = datetime.now()
        reminder_time = datetime.strptime(time_str, "%H:%M").replace(year=now.year, month=now.month, day=now.day)
        if reminder_time < now:
            reminder_time += timedelta(days=1)

        delta = (reminder_time - now).total_seconds()
        task = asyncio.create_task(reminder_task(bot, user_id, delta, text))
        user_tasks[user_id] = task
    except ValueError:
        return False
    return True

async def reminder_task(bot, user_id, delay, text):
    await asyncio.sleep(delay)
    await send_reminder(bot, user_id, text)
    user_tasks.pop(user_id, None)

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет! Отправь время и текст напоминания в формате: ЧЧ:ММ Текст.")

@router.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    match = re.match(r"(\d{1,2}:\d{2})\s+(.+)", message.text)
    if not match:
        await message.answer("❌ Неверный формат сообщения!")
        return
    time_str, reminder_text = match.groups()
    scheduled = await schedule_reminder(message.bot, user_id, time_str, reminder_text)
    if scheduled:
        await message.answer(f"✅ Напоминание установлено на {time_str}")
    else:
        await message.answer("❌ Неверный формат времени!")

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
