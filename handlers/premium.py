"""
Премиум-подписка через Telegram Stars и поддержка проекта.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from sqlalchemy.ext.asyncio import AsyncSession

from config import STAR_SUBSCRIPTION_PERIOD, SUPPORT_URL, Settings
from services.user_service import UserService
from utils.keyboards import premium_keyboard

logger = logging.getLogger(__name__)
router = Router(name="premium")

PREMIUM_PAYLOAD = "premium_subscription_30d"


def premium_description(price: int) -> str:
    """Текст описания Premium."""
    return (
        "⭐ <b>Premium «Слово Дня»</b>\n\n"
        "Что входит:\n"
        "📖 Личный словарь и избранное\n"
        "🌍 Изучение нескольких языков одновременно\n"
        "🎯 Расширенный квиз\n"
        "🔔 Приоритетная поддержка\n\n"
        f"💫 Стоимость: <b>{price} Stars</b> / 30 дней\n"
        "Оплата через Telegram Stars — безопасно и мгновенно."
    )


@router.message(Command("premium"))
@router.message(F.text == "⭐ Премиум")
async def cmd_premium(message: Message, settings: Settings) -> None:
    """Информация о Premium."""
    await message.answer(
        premium_description(settings.premium_stars_price),
        reply_markup=premium_keyboard(),
    )


@router.message(Command("support"))
async def cmd_support(message: Message) -> None:
    """Ссылка на поддержку проекта."""
    await message.answer(
        "💝 <b>Поддержать проект</b>\n\n"
        "Если вам нравится бот, вы можете поддержать его развитие:\n"
        f"👉 <a href=\"{SUPPORT_URL}\">Donatty — поддержка создателя</a>\n\n"
        "Спасибо! 🙏"
    )


@router.callback_query(F.data == "settings:premium")
async def settings_premium(callback: CallbackQuery, settings: Settings) -> None:
    """Premium из меню настроек."""
    await callback.message.edit_text(
        premium_description(settings.premium_stars_price),
        reply_markup=premium_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "premium:subscribe")
async def premium_subscribe(callback: CallbackQuery, settings: Settings) -> None:
    """Отправляет инвойс Telegram Stars."""
    try:
        await callback.message.answer_invoice(
            title="Premium «Слово Дня»",
            description="Подписка на 30 дней: словарь, избранное, мульти-языки",
            payload=PREMIUM_PAYLOAD,
            currency="XTR",
            prices=[
                LabeledPrice(
                    label="Premium 30 дней",
                    amount=settings.premium_stars_price,
                )
            ],
            subscription_period=STAR_SUBSCRIPTION_PERIOD,
            provider_token="",
        )
        await callback.answer()
    except Exception:
        logger.exception("Ошибка создания инвойса Stars")
        await callback.answer(
            "Не удалось создать счёт. Попробуйте позже.",
            show_alert=True,
        )


@router.pre_checkout_query(F.invoice_payload == PREMIUM_PAYLOAD)
async def pre_checkout(query: PreCheckoutQuery) -> None:
    """Подтверждение платежа перед списанием Stars."""
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    """Активация Premium после успешной оплаты."""
    payment = message.successful_payment
    if payment.invoice_payload != PREMIUM_PAYLOAD:
        return

    user_service = UserService(session)
    user = await user_service.get_or_create(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    is_subscription = payment.is_recurring or bool(payment.subscription_expiration_date)

    await user_service.activate_premium(
        user=user,
        charge_id=payment.telegram_payment_charge_id,
        amount=payment.total_amount,
        payload=payment.invoice_payload,
        is_subscription=is_subscription,
    )

    until = user.premium_until.strftime("%d.%m.%Y") if user.premium_until else "—"
    await message.answer(
        "🎉 <b>Спасибо за Premium!</b>\n\n"
        f"⭐ Подписка активна до: <b>{until}</b>\n"
        "📖 Теперь вам доступен личный словарь: /dictionary\n\n"
        f"💝 Поддержать проект: {SUPPORT_URL}"
    )
