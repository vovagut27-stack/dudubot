"""
Публичная страница статуса — открывается в браузере по ссылке Vercel.
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler


def _html() -> str:
    bot_username = os.getenv("BOT_USERNAME", "your_bot")
    support_url = "https://donatty.com/creator_bots"
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Слово Дня — Telegram Bot</title>
  <style>
    body {{
      font-family: system-ui, sans-serif;
      max-width: 640px; margin: 40px auto; padding: 0 20px;
      background: #0f172a; color: #e2e8f0; line-height: 1.6;
    }}
    h1 {{ color: #38bdf8; }}
    a {{ color: #fbbf24; }}
    .card {{
      background: #1e293b; border-radius: 12px; padding: 24px;
      margin: 20px 0; border: 1px solid #334155;
    }}
    .btn {{
      display: inline-block; background: #2563eb; color: white;
      padding: 12px 24px; border-radius: 8px; text-decoration: none;
      font-weight: 600; margin-top: 12px;
    }}
    .btn:hover {{ background: #1d4ed8; }}
    .ok {{ color: #4ade80; }}
  </style>
</head>
<body>
  <h1>📚 Слово Дня</h1>
  <div class="card">
    <p class="ok">✅ Сервер на Vercel работает</p>
    <p>Это Telegram-бот для изучения слов. Откройте его в Telegram:</p>
    <a class="btn" href="https://t.me/{bot_username}">Открыть бота в Telegram</a>
  </div>
  <div class="card">
    <p><b>Эндпоинты:</b></p>
    <ul>
      <li><code>/api/webhook</code> — приём сообщений от Telegram</li>
      <li><code>/api/cron_daily</code> — ежедневная рассылка</li>
      <li><code>/api/setup</code> — регистрация webhook (один раз)</li>
    </ul>
  </div>
  <p>💝 <a href="{support_url}">Поддержать проект</a></p>
</body>
</html>"""


class handler(BaseHTTPRequestHandler):
    """Vercel Serverless Function — GET /api/index или /"""

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(_html().encode("utf-8"))

    def do_HEAD(self) -> None:
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
