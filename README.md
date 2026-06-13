# 📚 Слово Дня — Telegram Bot

Ежедневный Telegram-бот для расширения словарного запаса на **английском**, **сербском**, **русском** и **белорусском** языках. С геймификацией, квизами и Premium-подпиской через **Telegram Stars**.

## ✨ Возможности

| Функция | Описание |
|---------|----------|
| `/start` | Приветствие и онбординг (уровень A1–C2, языки, время) |
| `/today` | Получить слово дня вручную |
| Рассылка | Автоматическая отправка в выбранное время |
| Геймификация | Очки, streak, уровень пользователя |
| Inline-кнопки | Выучил / Не знаю / Примеры / В словарь |
| `/stats` | Статистика прогресса |
| `/settings` | Изменение времени, уровня, языков |
| `/quiz` | Мини-квиз по выученным словам |
| `/dictionary` | Личный словарь (Premium) |
| `/premium` | Подписка через Telegram Stars |
| `/support` | Поддержка проекта на [Donatty](https://donatty.com/creator_bots) |

## 🏗 Структура проекта

```
word_of_the_day_bot/
├── main.py                 # Точка входа
├── bot.py                  # Инициализация aiogram
├── config.py               # Настройки из .env
├── database.py             # SQLAlchemy async
├── scheduler.py            # APScheduler рассылка
├── handlers/
│   ├── start.py            # /start, онбординг
│   ├── daily.py            # /today, inline-кнопки
│   ├── stats.py            # /stats
│   ├── settings.py         # /settings
│   ├── quiz.py             # /quiz
│   ├── dictionary.py       # /dictionary
│   ├── premium.py          # Stars, /support
│   └── middleware.py       # DB session
├── models/
│   └── models.py           # ORM-модели
├── services/
│   ├── word_service.py     # Слова из JSON
│   └── user_service.py     # Пользователи, геймификация
├── utils/
│   └── keyboards.py        # Клавиатуры
├── data/
│   └── words.json          # Словарь слов
├── alembic/                # Миграции БД
├── .env.example
├── requirements.txt
└── README.md
```

> **Деплой на Vercel (публичная ссылка в браузере):** см. [DEPLOY_VERCEL.md](DEPLOY_VERCEL.md)

## 🚀 Быстрый старт (локально)

### 1. Клонирование и окружение

```bash
cd word_of_the_day_bot
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Настройка

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # Linux/macOS
```

Откройте `.env` и укажите:

```env
BOT_TOKEN=123456:ABC-DEF...
TIMEZONE=Europe/Moscow
PREMIUM_STARS_PRICE=150
```

### 3. Получение токена бота

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. `/newbot` → следуйте инструкциям
3. Скопируйте токен в `.env`

### 4. Настройка Telegram Stars (монетизация)

1. В [@BotFather](https://t.me/BotFather): `/mybots` → ваш бот → **Payments**
2. Включите **Telegram Stars**
3. Premium-инвойс создаётся автоматически при нажатии «⭐ Оформить Premium»

### 5. Запуск

```bash
python main.py
```

### 6. Миграции (опционально, для production)

```bash
alembic upgrade head
```

> При первом запуске таблицы создаются автоматически через `create_all`.

## 🐘 PostgreSQL

Замените `DATABASE_URL` в `.env`:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/wordbot
```

## 📖 Добавление слов

Редактируйте `data/words.json`:

```json
{
  "key": "en_b1_example",
  "language": "en",
  "level": "B1",
  "word": "example",
  "translation": "пример",
  "transcription": "/ɪɡˈzæmpəl/",
  "part_of_speech": "noun",
  "examples": ["This is an example."]
}
```

После изменений перезапустите бота.

## 💳 Premium и поддержка

- **Premium** — оплата Telegram Stars (подписка 30 дней)
- **Поддержка проекта** — [https://donatty.com/creator_bots](https://donatty.com/creator_bots)

Premium открывает:
- 📖 Личный словарь
- ⭐ Избранные слова
- 🌍 Одновременное изучение нескольких языков

## 🛠 Технологии

- [aiogram 3.x](https://docs.aiogram.dev/) — Telegram Bot API
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/) — async ORM
- [APScheduler](https://apscheduler.readthedocs.io/) — планировщик
- [Alembic](https://alembic.sqlalchemy.org/) — миграции
- SQLite / PostgreSQL

## 📋 Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Начать / онбординг |
| `/today` | Слово дня |
| `/stats` | Статистика |
| `/settings` | Настройки |
| `/quiz` | Квиз |
| `/dictionary` | Словарь (Premium) |
| `/premium` | Подписка Stars |
| `/support` | Поддержка Donatty |

## 📄 Лицензия

MIT — используйте свободно для обучения и коммерческих проектов.

---

Сделано с ❤️ для изучения языков
