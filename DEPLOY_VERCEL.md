# Деплой «Слово Дня» на Vercel — пошаговая инструкция для новичков

## Важно понять перед началом

| Локально (`python main.py`) | На Vercel |
|-----------------------------|-----------|
| Бот работает 24/7 на вашем ПК | Бот «просыпается» только когда приходит запрос |
| Режим **polling** (сам опрашивает Telegram) | Режим **webhook** (Telegram шлёт сообщения на URL) |
| SQLite — файл на диске | **Нужна облачная PostgreSQL** (SQLite на Vercel не сохраняется) |
| APScheduler внутри процесса | **Vercel Cron** — отдельный вызов каждую минуту |

**Публичная ссылка в браузере** после деплоя:
```
https://ВАШ-ПРОЕКТ.vercel.app
```
Там будет страница статуса. Сам бот открывается в Telegram:
```
https://t.me/ВАШ_BOT_USERNAME
```

---

## Шаг 0. Что понадобится (бесплатно)

1. Аккаунт [GitHub](https://github.com)
2. Аккаунт [Vercel](https://vercel.com)
3. Аккаунт [Neon](https://neon.tech) — бесплатная PostgreSQL
4. Бот в Telegram через [@BotFather](https://t.me/BotFather)

---

## Шаг 1. Создайте Telegram-бота

1. Откройте Telegram → [@BotFather](https://t.me/BotFather)
2. Отправьте `/newbot`
3. Введите **имя** (например: `Слово Дня`)
4. Введите **username** латиницей (например: `my_word_day_bot`)
5. BotFather пришлёт **токен** вида:
   ```
   7123456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```
6. **Сохраните токен** — это `BOT_TOKEN`

Запомните username бота (без `@`) — это `BOT_USERNAME`.

---

## Шаг 2. Создайте базу данных PostgreSQL (Neon)

> SQLite на Vercel **не работает** — данные пользователей пропадут после каждого запроса.

1. Зайдите на [neon.tech](https://neon.tech) → **Sign Up** (можно через GitHub)
2. **New Project** → название `word-day-bot` → **Create**
3. На Dashboard найдите **Connection string** → выберите **URI**
4. Скопируйте строку вида:
   ```
   postgres://user:password@ep-xxx.region.aws.neon.tech/neondb?sslmode=require
   ```
5. Это ваш `DATABASE_URL` (код сам преобразует в `postgresql+asyncpg://`)

---

## Шаг 3. Загрузите код на GitHub

### 3.1 Установите Git
Скачайте: [git-scm.com/downloads](https://git-scm.com/downloads)

### 3.2 Создайте репозиторий на GitHub
1. [github.com/new](https://github.com/new)
2. Имя: `word-of-the-day-bot`
3. **Create repository**

### 3.3 Загрузите проект из PowerShell

```powershell
cd "c:\Users\нонаме\OneDrive\Duolingo\word_of_the_day_bot"

git init
git add .
git commit -m "Initial commit: Word of the Day bot"
git branch -M main
git remote add origin https://github.com/ВАШ_ЛОГИН/word-of-the-day-bot.git
git push -u origin main
```

Замените `ВАШ_ЛОГИН` на ваш GitHub username.

---

## Шаг 4. Задеплойте на Vercel

### 4.1 Подключите GitHub
1. [vercel.com](https://vercel.com) → **Sign Up** → через GitHub
2. **Add New… → Project**
3. Выберите репозиторий `word-of-the-day-bot`
4. **Framework Preset:** Other
5. **Root Directory:** `./` (корень репозитория)

### 4.2 Добавьте переменные окружения

Нажмите **Environment Variables** и добавьте:

| Имя | Значение | Пример |
|-----|----------|--------|
| `BOT_TOKEN` | Токен от BotFather | `7123456789:AAH...` |
| `BOT_USERNAME` | Username бота без @ | `my_word_day_bot` |
| `DATABASE_URL` | Строка из Neon | `postgres://user:pass@ep-...` |
| `TIMEZONE` | Часовой пояс | `Europe/Moscow` |
| `SETUP_SECRET` | Любая случайная строка | `mySetupSecret2024xyz` |
| `WEBHOOK_SECRET` | Другая случайная строка | `webhookSecretAbc123` |
| `CRON_SECRET` | Ещё одна случайная строка | `cronSecretDef456` |
| `PREMIUM_STARS_PRICE` | Цена Premium | `150` |

> **Как придумать секрет:** наберите случайные 20+ символов или используйте [random.org/strings](https://www.random.org/strings/)

### 4.3 Нажмите Deploy

Подождите 1–3 минуты. Vercel покажет:
```
🎉 Congratulations!
https://word-of-the-day-bot-xxxxx.vercel.app
```

**Это ваша публичная ссылка для браузера.**

---

## Шаг 5. Подключите бота к Vercel (webhook)

После деплоя Telegram ещё **не знает**, куда слать сообщения. Нужно один раз зарегистрировать webhook.

Откройте в браузере (подставьте свои значения):

```
https://word-of-the-day-bot-xxxxx.vercel.app/api/setup?secret=ВАШ_SETUP_SECRET
```

Если всё OK, увидите JSON:
```json
{
  "ok": true,
  "webhook_url": "https://word-of-the-day-bot-xxxxx.vercel.app/api/webhook",
  "telegram_url": "https://word-of-the-day-bot-xxxxx.vercel.app/api/webhook",
  "pending_updates": 0
}
```

---

## Шаг 6. Проверьте работу

### В браузере
Откройте:
```
https://word-of-the-day-bot-xxxxx.vercel.app
```
Должна появиться страница «✅ Сервер на Vercel работает».

### В Telegram
1. Откройте `https://t.me/ВАШ_BOT_USERNAME`
2. Нажмите **Start** или отправьте `/start`
3. Пройдите онбординг
4. Попробуйте `/today`

---

## Шаг 7. Ежедневная рассылка (Cron)

В проекте уже настроен `vercel.json`:
```json
"crons": [{ "path": "/api/cron/daily", "schedule": "* * * * *" }]
```

Это вызывает рассылку **каждую минуту** (чтобы попасть в выбранное пользователем время).

### Ограничения бесплатного плана Vercel (Hobby)
- Cron на Hobby может работать **не каждую минуту** (best-effort)
- Для точной рассылки по минутам нужен **Pro** ($20/мес) или внешний cron

**Бесплатная альтернатива:** [cron-job.org](https://cron-job.org)
1. Создайте задачу → URL: `https://ВАШ-ПРОЕКТ.vercel.app/api/cron/daily`
2. Расписание: каждую минуту
3. Заголовок: `Authorization: Bearer ВАШ_CRON_SECRET`

---

## Шаг 8. Обновление бота

После изменений в коде:

```powershell
git add .
git commit -m "Update bot"
git push
```

Vercel **автоматически** пересоберёт проект за 1–2 минуты.

После смены домена или первого деплоя **повторите Шаг 5** (`/api/setup`).

---

## Частые ошибки

### Бот не отвечает в Telegram
- Проверьте, что выполнили **Шаг 5** (`/api/setup`)
- Проверьте `BOT_TOKEN` в Vercel → Settings → Environment Variables
- Vercel → Project → **Logs** — смотрите ошибки

### `Forbidden: wrong or missing ?secret=`
- В URL должен быть правильный `SETUP_SECRET` из переменных Vercel

### Ошибки базы данных
- `DATABASE_URL` должен быть из Neon (не SQLite)
- Проверьте, что проект Neon **не приостановлен** (free tier засыпает — первый запрос может быть медленным)

### Квиз / онбординг «сбрасывается»
- На serverless состояние FSM хранится в памяти и может теряться между запросами
- Для production лучше VPS/Railway/Render с `python main.py`

---

## Схема работы на Vercel

```
Пользователь пишет боту в Telegram
         ↓
Telegram отправляет POST → https://ваш-проект.vercel.app/api/webhook
         ↓
Vercel запускает Python-функцию → aiogram обрабатывает сообщение
         ↓
Ответ уходит пользователю в Telegram

Каждую минуту Vercel Cron → /api/cron/daily → рассылка слова дня
```

---

## Если Vercel кажется сложным

Для Telegram-ботов проще подойдут:
- **[Railway](https://railway.app)** — запуск `python main.py` без переделок
- **[Render](https://render.com)** — бесплатный Background Worker
- **VPS** (Timeweb, Hetzner) — полный контроль

На этих платформах работает оригинальный `main.py` без webhook.

---

## Ваши ссылки после деплоя

| Назначение | URL |
|------------|-----|
| Страница в браузере | `https://ВАШ-ПРОЕКТ.vercel.app` |
| Бот в Telegram | `https://t.me/ВАШ_BOT_USERNAME` |
| Регистрация webhook | `https://ВАШ-ПРОЕКТ.vercel.app/api/setup?secret=SETUP_SECRET` |

Удачи! 🚀
