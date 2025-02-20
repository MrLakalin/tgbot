# Telegram Reminder Bot

## [![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/) [![aiogram](https://img.shields.io/badge/aiogram-3.x-green.svg)](https://docs.aiogram.dev/)

### Простой и удобный бот для Telegram, который помогает вам устанавливать напоминания. Бот сохраняет ваши напоминания и позволяет отправлять в нужный момент. Бот @NapomniTimeBot

---

## Содержание

1. ## Особенности
2. ## Требования
3. ## Использование
4. ## Команды
5. ## Советы по использованию
6. ## Структура проекта
   
---

## Особенности

- **Установка напоминаний**: Устанавливайте напоминания на будущее с указанием даты, времени и текста.
- **Просмотр напоминаний**: Просматривайте список всех активных напоминаний.
- **Редактирование напоминаний**: Изменяйте время или текст существующих напоминаний.
- **Удаление напоминаний**: Удаляйте ненужные напоминания в любой момент.
- **Сохранение данных**: Все напоминания сохраняются в файле `reminders.json`, чтобы они не пропадали при перезапуске бота.

---

## Требования

- Python 3.8 или новее
- Библиотека `aiogram` версии 3.x
- Файл конфигурации `.env` с токеном бота

---

## Использование

- **/start**: Запустить бота и получить приветственное сообщение.
- **/help**: Получить справку по использованию бота.
- **Установить напоминание**: Начать процесс установки нового напоминания.
- **Мои напоминания**: Просмотреть все активные напоминания.
- **Изменить напоминание**: Изменить существующее напоминание.
- **Удалить напоминания**: Удалить одно или несколько напоминаний.

---

## Советы по использованию
- **Формат даты и времени** : Всегда используйте формат `ДД.ММ.ГГГГ ЧЧ:MM`, чтобы избежать ошибок.
- **Напоминания в прошлом** : Бот не позволит установить напоминание на прошедшее время.

---

## Структура проекта
```
telegram-reminder-bot/
├── run.py # Главный файл бота
├── reminders.json # Файл для хранения напоминаний
├── keyboard.py # Файл с определением клавиатур
├── set.py # Файл со всеми функциями
└── README.md # Этот файл
```
