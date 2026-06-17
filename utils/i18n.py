"""
Локализация интерфейса бота.
"""

from __future__ import annotations

from config import SUPPORTED_LANGUAGES, UI_LANGUAGES

DEFAULT_UI_LANGUAGE = "ru"

MESSAGES: dict[str, dict[str, str]] = {
    "ru": {
        "btn_today": "📚 Слово дня",
        "btn_stats": "📊 Статистика",
        "btn_settings": "⚙️ Настройки",
        "btn_quiz": "🎯 Квиз",
        "btn_dictionary": "📖 Мой словарь",
        "btn_premium": "⭐ Премиум",
        "menu_placeholder": "Выберите действие…",
        "welcome_title": "👋 <b>Добро пожаловать в «Слово Дня»!</b>",
        "welcome_body": (
            "Каждый день вы будете получать новые слова на выбранных языках:\n"
            "{languages}\n\n"
            "🎮 Зарабатывайте очки, поддерживайте streak и проходите квизы!\n\n"
            "Давайте настроим ваш профиль 👇"
        ),
        "welcome_back": "С возвращением, {name}! 🌟\nИспользуйте меню или команды.",
        "onboard_first": "Сначала пройдите онбординг: /start",
        "settings_title": "⚙️ <b>Настройки</b>",
        "settings_level_line": "📊 Уровень: <b>{level}</b>",
        "settings_langs_line": "🌍 Языки: {langs}",
        "settings_ui_line": "💬 Язык интерфейса: <b>{ui_name}</b>",
        "settings_time_line": "🕐 Уведомления: <b>{time}</b>",
        "settings_time_btn": "🕐 Время уведомлений",
        "settings_level_btn": "📊 Уровень CEFR",
        "settings_langs_btn": "🌍 Языки для изучения",
        "settings_ui_btn": "💬 Язык интерфейса",
        "settings_premium_btn": "⭐ Премиум / Поддержка",
        "settings_back": "◀️ Назад",
        "settings_choose_level": "📊 Выберите уровень CEFR:",
        "settings_choose_time": "🕐 Выберите время утренней рассылки:\n(07:00 · 08:00 · 09:00 · 12:00 · 18:00 · 20:00 · 21:00)",
        "settings_choose_langs": "🌍 Выберите языки для изучения (можно несколько):",
        "settings_choose_langs_free": "🌍 Выберите языки для изучения (Free — до {max}):",
        "settings_choose_langs_premium": "🌍 Выберите языки для изучения (Premium — безлимит):",
        "settings_langs_limit_free": "На Free можно выбрать не более {max} языков. Premium — безлимит: /premium",
        "settings_langs_limit_save": "Сохранение невозможно: на Free — не более {max} языков. Уберите лишние или оформите Premium.",
        "settings_choose_ui": "💬 Выберите язык интерфейса бота:",
        "settings_level_saved": "Уровень: {level} ✅",
        "settings_time_saved": "Время: {time} ✅",
        "settings_langs_saved": "Языки сохранены ✅",
        "settings_ui_saved": "Язык интерфейса: {ui_name} ✅",
        "settings_select_lang": "Выберите хотя бы один язык!",
        "onboard_level_ok": "✅ Уровень: <b>{level}</b>",
        "onboard_choose_langs": "🌍 Выберите один или несколько языков для изучения:",
        "onboard_choose_langs_free": "🌍 Выберите языки для изучения (Free — до {max}):",
        "onboard_choose_langs_premium": "🌍 Выберите языки для изучения (Premium — безлимит):",
        "onboard_langs_ok": "🌍 Языки: {langs}",
        "onboard_choose_time": "🕐 В какое время утром присылать слова дня?\n(07:00 · 08:00 · 09:00 · 12:00 · 18:00 · 20:00 · 21:00)",
        "onboard_done": (
            "🎉 <b>Настройка завершена!</b>\n\n"
            "📊 Уровень: <b>{level}</b>\n"
            "🌍 Языки: {langs}\n"
            "🕐 Уведомления: <b>{time}</b>\n\n"
            "Нажмите /today чтобы получить первое слово!"
        ),
        "onboard_main_menu": "Главное меню 👇",
        "btn_done": "✔️ Готово",
        "btn_save": "💾 Сохранить",
        "error_generic": "Ошибка",
    },
    "en": {
        "btn_today": "📚 Word of the day",
        "btn_stats": "📊 Statistics",
        "btn_settings": "⚙️ Settings",
        "btn_quiz": "🎯 Quiz",
        "btn_dictionary": "📖 My dictionary",
        "btn_premium": "⭐ Premium",
        "menu_placeholder": "Choose an action…",
        "welcome_title": "👋 <b>Welcome to Word of the Day!</b>",
        "welcome_body": (
            "Every day you'll receive new words in your chosen languages:\n"
            "{languages}\n\n"
            "🎮 Earn points, keep your streak, and take quizzes!\n\n"
            "Let's set up your profile 👇"
        ),
        "welcome_back": "Welcome back, {name}! 🌟\nUse the menu or commands.",
        "onboard_first": "Please complete onboarding first: /start",
        "settings_title": "⚙️ <b>Settings</b>",
        "settings_level_line": "📊 Level: <b>{level}</b>",
        "settings_langs_line": "🌍 Languages: {langs}",
        "settings_ui_line": "💬 Interface language: <b>{ui_name}</b>",
        "settings_time_line": "🕐 Notifications: <b>{time}</b>",
        "settings_time_btn": "🕐 Notification time",
        "settings_level_btn": "📊 CEFR level",
        "settings_langs_btn": "🌍 Study languages",
        "settings_ui_btn": "💬 Interface language",
        "settings_premium_btn": "⭐ Premium / Support",
        "settings_back": "◀️ Back",
        "settings_choose_level": "📊 Choose your CEFR level:",
        "settings_choose_time": "🕐 Choose notification time:",
        "settings_choose_langs": "🌍 Choose study languages (multiple allowed):",
        "settings_choose_langs_free": "🌍 Choose study languages (Free — up to {max}):",
        "settings_choose_langs_premium": "🌍 Choose study languages (Premium — unlimited):",
        "settings_langs_limit_free": "Free plan allows up to {max} languages. Premium is unlimited: /premium",
        "settings_langs_limit_save": "Can't save: Free allows up to {max} languages. Remove extras or get Premium.",
        "settings_choose_ui": "💬 Choose bot interface language:",
        "settings_level_saved": "Level: {level} ✅",
        "settings_time_saved": "Time: {time} ✅",
        "settings_langs_saved": "Languages saved ✅",
        "settings_ui_saved": "Interface language: {ui_name} ✅",
        "settings_select_lang": "Select at least one language!",
        "onboard_level_ok": "✅ Level: <b>{level}</b>",
        "onboard_choose_langs": "🌍 Choose one or more languages to study:",
        "onboard_choose_langs_free": "🌍 Choose study languages (Free — up to {max}):",
        "onboard_choose_langs_premium": "🌍 Choose study languages (Premium — unlimited):",
        "onboard_langs_ok": "🌍 Languages: {langs}",
        "onboard_choose_time": "🕐 When should we send your daily words?\n(07:00 · 08:00 · 09:00 · 12:00 · 18:00 · 20:00 · 21:00)",
        "onboard_done": (
            "🎉 <b>Setup complete!</b>\n\n"
            "📊 Level: <b>{level}</b>\n"
            "🌍 Languages: {langs}\n"
            "🕐 Notifications: <b>{time}</b>\n\n"
            "Tap /today to get your first word!"
        ),
        "onboard_main_menu": "Main menu 👇",
        "btn_done": "✔️ Done",
        "btn_save": "💾 Save",
        "error_generic": "Error",
    },
    "de": {
        "btn_today": "📚 Wort des Tages",
        "btn_stats": "📊 Statistik",
        "btn_settings": "⚙️ Einstellungen",
        "btn_quiz": "🎯 Quiz",
        "btn_dictionary": "📖 Mein Wörterbuch",
        "btn_premium": "⭐ Premium",
        "menu_placeholder": "Aktion wählen…",
        "welcome_title": "👋 <b>Willkommen bei «Wort des Tages»!</b>",
        "welcome_body": (
            "Jeden Tag erhalten Sie neue Wörter in Ihren gewählten Sprachen:\n"
            "{languages}\n\n"
            "🎮 Sammeln Sie Punkte, halten Sie Ihre Serie und machen Sie Quizze!\n\n"
            "Richten wir Ihr Profil ein 👇"
        ),
        "welcome_back": "Willkommen zurück, {name}! 🌟\nNutzen Sie das Menü oder Befehle.",
        "onboard_first": "Bitte zuerst Onboarding abschließen: /start",
        "settings_title": "⚙️ <b>Einstellungen</b>",
        "settings_level_line": "📊 Niveau: <b>{level}</b>",
        "settings_langs_line": "🌍 Sprachen: {langs}",
        "settings_ui_line": "💬 Oberflächensprache: <b>{ui_name}</b>",
        "settings_time_line": "🕐 Benachrichtigungen: <b>{time}</b>",
        "settings_time_btn": "🕐 Benachrichtigungszeit",
        "settings_level_btn": "📊 CEFR-Niveau",
        "settings_langs_btn": "🌍 Lernsprachen",
        "settings_ui_btn": "💬 Oberflächensprache",
        "settings_premium_btn": "⭐ Premium / Unterstützung",
        "settings_back": "◀️ Zurück",
        "settings_choose_level": "📊 Wählen Sie Ihr CEFR-Niveau:",
        "settings_choose_time": "🕐 Wählen Sie die Benachrichtigungszeit:",
        "settings_choose_langs": "🌍 Wählen Sie Lernsprachen (mehrere möglich):",
        "settings_choose_langs_free": "🌍 Wählen Sie Lernsprachen (Free — bis {max}):",
        "settings_choose_langs_premium": "🌍 Wählen Sie Lernsprachen (Premium — unbegrenzt):",
        "settings_langs_limit_free": "Im Free-Tarif maximal {max} Sprachen. Premium ist unbegrenzt: /premium",
        "settings_langs_limit_save": "Speichern nicht möglich: Free erlaubt maximal {max} Sprachen. Entfernen Sie Sprachen oder holen Sie Premium.",
        "settings_choose_ui": "💬 Wählen Sie die Bot-Oberflächensprache:",
        "settings_level_saved": "Niveau: {level} ✅",
        "settings_time_saved": "Zeit: {time} ✅",
        "settings_langs_saved": "Sprachen gespeichert ✅",
        "settings_ui_saved": "Oberflächensprache: {ui_name} ✅",
        "settings_select_lang": "Wählen Sie mindestens eine Sprache!",
        "onboard_level_ok": "✅ Niveau: <b>{level}</b>",
        "onboard_choose_langs": "🌍 Wählen Sie eine oder mehrere Lernsprachen:",
        "onboard_choose_langs_free": "🌍 Wählen Sie Lernsprachen (Free — bis {max}):",
        "onboard_choose_langs_premium": "🌍 Wählen Sie Lernsprachen (Premium — unbegrenzt):",
        "onboard_langs_ok": "🌍 Sprachen: {langs}",
        "onboard_choose_time": "🕐 Wann sollen die Wörter des Tages gesendet werden?\n(07:00 · 08:00 · 09:00 · 12:00 · 18:00 · 20:00 · 21:00)",
        "onboard_done": (
            "🎉 <b>Einrichtung abgeschlossen!</b>\n\n"
            "📊 Niveau: <b>{level}</b>\n"
            "🌍 Sprachen: {langs}\n"
            "🕐 Benachrichtigungen: <b>{time}</b>\n\n"
            "Tippen Sie /today für Ihr erstes Wort!"
        ),
        "onboard_main_menu": "Hauptmenü 👇",
        "btn_done": "✔️ Fertig",
        "btn_save": "💾 Speichern",
        "error_generic": "Fehler",
    },
    "it": {
        "btn_today": "📚 Parola del giorno",
        "btn_stats": "📊 Statistiche",
        "btn_settings": "⚙️ Impostazioni",
        "btn_quiz": "🎯 Quiz",
        "btn_dictionary": "📖 Il mio dizionario",
        "btn_premium": "⭐ Premium",
        "menu_placeholder": "Scegli un'azione…",
        "welcome_title": "👋 <b>Benvenuto in «Parola del Giorno»!</b>",
        "welcome_body": (
            "Ogni giorno riceverai nuove parole nelle lingue scelte:\n"
            "{languages}\n\n"
            "🎮 Guadagna punti, mantieni la serie e fai i quiz!\n\n"
            "Configuriamo il tuo profilo 👇"
        ),
        "welcome_back": "Bentornato, {name}! 🌟\nUsa il menu o i comandi.",
        "onboard_first": "Completa prima l'onboarding: /start",
        "settings_title": "⚙️ <b>Impostazioni</b>",
        "settings_level_line": "📊 Livello: <b>{level}</b>",
        "settings_langs_line": "🌍 Lingue: {langs}",
        "settings_ui_line": "💬 Lingua interfaccia: <b>{ui_name}</b>",
        "settings_time_line": "🕐 Notifiche: <b>{time}</b>",
        "settings_time_btn": "🕐 Orario notifiche",
        "settings_level_btn": "📊 Livello CEFR",
        "settings_langs_btn": "🌍 Lingue da studiare",
        "settings_ui_btn": "💬 Lingua interfaccia",
        "settings_premium_btn": "⭐ Premium / Supporto",
        "settings_back": "◀️ Indietro",
        "settings_choose_level": "📊 Scegli il livello CEFR:",
        "settings_choose_time": "🕐 Scegli l'orario delle notifiche:",
        "settings_choose_langs": "🌍 Scegli le lingue da studiare (puoi selezionarne più di una):",
        "settings_choose_langs_free": "🌍 Scegli le lingue da studiare (Free — fino a {max}):",
        "settings_choose_langs_premium": "🌍 Scegli le lingue da studiare (Premium — illimitate):",
        "settings_langs_limit_free": "Il piano Free consente al massimo {max} lingue. Premium è illimitato: /premium",
        "settings_langs_limit_save": "Impossibile salvare: Free consente al massimo {max} lingue. Rimuovi quelle extra o attiva Premium.",
        "settings_choose_ui": "💬 Scegli la lingua dell'interfaccia del bot:",
        "settings_level_saved": "Livello: {level} ✅",
        "settings_time_saved": "Orario: {time} ✅",
        "settings_langs_saved": "Lingue salvate ✅",
        "settings_ui_saved": "Lingua interfaccia: {ui_name} ✅",
        "settings_select_lang": "Seleziona almeno una lingua!",
        "onboard_level_ok": "✅ Livello: <b>{level}</b>",
        "onboard_choose_langs": "🌍 Scegli una o più lingue da studiare:",
        "onboard_choose_langs_free": "🌍 Scegli le lingue da studiare (Free — fino a {max}):",
        "onboard_choose_langs_premium": "🌍 Scegli le lingue da studiare (Premium — illimitate):",
        "onboard_langs_ok": "🌍 Lingue: {langs}",
        "onboard_choose_time": "🕐 A che ora inviare le parole del giorno?\n(07:00 · 08:00 · 09:00 · 12:00 · 18:00 · 20:00 · 21:00)",
        "onboard_done": (
            "🎉 <b>Configurazione completata!</b>\n\n"
            "📊 Livello: <b>{level}</b>\n"
            "🌍 Lingue: {langs}\n"
            "🕐 Notifiche: <b>{time}</b>\n\n"
            "Premi /today per la tua prima parola!"
        ),
        "onboard_main_menu": "Menu principale 👇",
        "btn_done": "✔️ Fatto",
        "btn_save": "💾 Salva",
        "error_generic": "Errore",
    },
}


def normalize_ui_language(code: str | None) -> str:
    """Возвращает поддерживаемый код языка интерфейса."""
    if code and code in UI_LANGUAGES:
        return code
    return DEFAULT_UI_LANGUAGE


def t(locale: str, message_key: str, **format_kwargs: str) -> str:
    """Перевод строки по ключу.

    Первый аргумент — код языка интерфейса (`locale`), не путать с плейсхолдерами
    вроде ``{ui_name}`` в шаблонах.
    """
    reserved = {"locale", "message_key"}
    conflict = reserved & format_kwargs.keys()
    if conflict:
        names = ", ".join(sorted(conflict))
        raise TypeError(f"t() got reserved format kwargs: {names}")

    locale = normalize_ui_language(locale)
    text = MESSAGES.get(locale, MESSAGES[DEFAULT_UI_LANGUAGE]).get(
        message_key, MESSAGES[DEFAULT_UI_LANGUAGE][message_key]
    )
    return text.format(**format_kwargs) if format_kwargs else text


def all_texts(key: str) -> tuple[str, ...]:
    """Все варианты текста кнопки для фильтров aiogram."""
    return tuple(
        messages[key]
        for messages in MESSAGES.values()
        if key in messages
    )


def supported_languages_list() -> str:
    """Строка со всеми языками для изучения."""
    return " · ".join(SUPPORTED_LANGUAGES.values())
