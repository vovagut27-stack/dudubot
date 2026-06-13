"""Фильтры для кнопок главного меню на всех языках интерфейса."""

from __future__ import annotations

from aiogram import F

from utils.i18n import all_texts


def menu_btn(key: str):
    """Фильтр текста reply-кнопки по ключу i18n."""
    return F.text.in_(all_texts(key))
