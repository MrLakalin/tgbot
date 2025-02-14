# Telegram Reminder Bot

## [![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/) [![aiogram](https://img.shields.io/badge/aiogram-3.x-green.svg)](https://docs.aiogram.dev/)

### Простой и удобный бот для Telegram, который помогает вам устанавливать напоминания. Бот сохраняет ваши напоминания между перезапусками и позволяет управлять ими через интуитивный интерфейс.

---

## Содержание

1. ## Особенности
2. ## Требования
3. ## Использование
4. ## Команды
5. ## Структура проекта

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
После запуска бота добавьте его в свой Telegram и начните взаимодействие. Вот основные шаги:

Отправьте команду `/start`, чтобы начать работу с ботом.
1. Выберите действие из меню:
- **Установить напоминание**
- **Мои напоминания**
- **Удалить напоминание**
- **Изменить напоминание**
2. Следуйте инструкциям бота для выполнения выбранного действия.
  
## Команды
| Команда / Действие                | Формат ввода                                                                 | Описание                                                                 |
|-----------------------------------|-----------------------------------------------------------------------------|-------------------------------------------------------------------------|
| `/start`                          |                                                                             | Начать работу с ботом.                                                  |
| **Установить напоминание**        | `ДД.ММ.ГГГГ ЧЧ:MM Текст_напоминания`                                        | Установить новое напоминание.                                           |
|                                   | Пример: `25.12.2023 18:30 Позвонить маме`                                    |                                                                         |
| **Мои напоминания**               |                                                                             | Получить список всех активных напоминаний.                              |
| **Удалить напоминание**           | `ID`                                                                        | Удалить напоминание по его ID.                                          |
|                                   | Пример: `1`                                                                 |                                                                         |
| **Изменить напоминание**          | `ID ДД.ММ.ГГГГ ЧЧ:MM Новый_текст_напоминания`                                | Изменить время или текст существующего напоминания.                     |
|                                   | Пример: `1 26.12.2023 19:00 Не забыть купить молоко`                         |                                                                         |
