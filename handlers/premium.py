"""
Премиум-подписка через Telegram Stars и поддержка проекта.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from sqlalchemy.ext.asyncio import AsyncSession

from config import DAILY_WORDS_FREE_PER_LANGUAGE, DAILY_WORDS_PREMIUM, FREE_MAX_LANGUAGES, STAR_SUBSCRIPTION_PERIOD, SUPPORT_URL, Settings
from handlers.premium_grant_cmd import reply_premium_granted
from services.user_service import UserService
from utils.i18n import normalize_ui_language, t
from utils.kb import main_menu_keyboard, premium_keyboard
from utils.menu_filters import menu_btn
from utils.setup_auth import check_premium_activation_code, looks_like_activation_code

logger = logging.getLogger(__name__)
router = Router(name="premium")

PREMIUM_PAYLOAD = "premium_subscription_30d"


def _premium_prices(price: int) -> list[LabeledPrice]:
    """Одна позиция в счёте — требование Telegram Stars."""
    return [LabeledPrice(label="Premium 30 дней", amount=price)]


async def send_premium_invoice(bot, chat_id: int, price: int) -> None:
    """
    Отправляет счёт Telegram Stars.

    Подписки (subscription_period) нельзя отправлять через sendInvoice —
    только через createInvoiceLink. Поэтому сначала пробуем ссылку на подписку,
    затем разовый платёж без автопродления.
    """
    title = "Premium Слово Дня"
    description = "30 дней: словарь, избранное, до 10 слов в день"
    prices = _premium_prices(price)

    try:
        link = await bot.create_invoice_link(
            title=title,
            description=description,
            payload=PREMIUM_PAYLOAD,
            provider_token="",
            currency="XTR",
            prices=prices,
            subscription_period=STAR_SUBSCRIPTION_PERIOD,
        )
        await bot.send_message(
            chat_id,
            f"⭐ Нажмите кнопку, чтобы оформить Premium за <b>{price} Stars</b> в месяц:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=f"⭐ Оплатить {price} Stars", url=link)],
                ]
            ),
        )
        return
    except TelegramBadRequest as exc:
        logger.warning(
            "create_invoice_link (subscription) failed, fallback to one-time: %s",
            exc.message,
        )

    await bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=PREMIUM_PAYLOAD,
        provider_token="",
        currency="XTR",
        prices=prices,
    )


def premium_description(price: int) -> str:
    """Текст описания Premium."""
    return (
        "⭐ <b>Premium «Слово Дня»</b>\n\n"
        "Что входит:\n"
        f"📬 <b>{DAILY_WORDS_PREMIUM} слов в день</b> "
        f"(Free — {DAILY_WORDS_FREE_PER_LANGUAGE} на каждый язык)\n"
        f"🌍 <b>Безлимит языков</b> (Free — до {FREE_MAX_LANGUAGES})\n"
        "📖 Личный словарь и избранное\n"
        "💬 Переводы всех примеров предложений\n"
        "🎯 Premium-квизы: расширенный, обратный, мультиязычный\n"
        "🔔 Приоритетная поддержка\n\n"
        f"💫 Стоимость: <b>{price} Stars</b> / 30 дней\n"
        "Оплата через Telegram Stars — безопасно и мгновенно.\n\n"
        "🧪 Тест (с кодом): <code>/premium ВАШ_КОД</code> или <code>/test_premium ВАШ_КОД</code>"
    )


@router.message(Command("premium"))
@router.message(menu_btn("btn_premium"))
async def cmd_premium(message: Message, settings: Settings, session: AsyncSession) -> None:
    """Информация о Premium или активация по коду."""
    if not message.from_user:
        return

    parts = (message.text or "").split(maxsplit=1)
    if len(parts) > 1:
        code = parts[1].strip()
        if check_premium_activation_code(code):
            await reply_premium_granted(message, message.from_user.id)
            return
        if looks_like_activation_code(code):
            await message.answer(
                "❌ <b>Неверный код.</b> Используйте код из <code>PREMIUM_ACTIVATION_CODE</code> "
                "или оформите подписку кнопкой ниже.\n"
                "Формат: <code>/premium ВАШ_КОД</code>"
            )
            return

    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(message.from_user.id)
    ui = normalize_ui_language(user.ui_language) if user else "ru"
    await message.answer(
        premium_description(settings.premium_stars_price),
        reply_markup=premium_keyboard(ui, from_settings=False),
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
async def settings_premium(callback: CallbackQuery, settings: Settings, session: AsyncSession) -> None:
    """Premium из меню настроек."""
    if callback.message is None:
        await callback.answer()
        return
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    ui = normalize_ui_language(user.ui_language) if user else "ru"
    await callback.message.edit_text(
        premium_description(settings.premium_stars_price),
        reply_markup=premium_keyboard(ui, from_settings=True),
    )
    await callback.answer()


@router.callback_query(F.data == "premium:back")
async def premium_back(callback: CallbackQuery, session: AsyncSession) -> None:
    """Возврат в главное меню из экрана Premium."""
    if callback.message is None:
        await callback.answer()
        return
    user_service = UserService(session)
    user = await user_service.get_by_telegram_id(callback.from_user.id)
    ui = normalize_ui_language(user.ui_language) if user else "ru"
    await callback.message.delete()
    await callback.message.answer(
        t(ui, "onboard_main_menu"),
        reply_markup=main_menu_keyboard(ui),
    )
    await callback.answer()


@router.callback_query(F.data == "premium:subscribe")
async def premium_subscribe(callback: CallbackQuery, settings: Settings) -> None:
    """Отправляет инвойс Telegram Stars."""
    price = settings.premium_stars_price
    if price < 1:
        await callback.answer("Premium временно недоступен.", show_alert=True)
        return

    try:
        await send_premium_invoice(callback.bot, callback.from_user.id, price)
        await callback.answer()
    except TelegramBadRequest as exc:
        logger.error("Ошибка создания инвойса Stars: %s", exc.message)
        hint = (
            "Не удалось создать счёт.\n\n"
            "Проверьте в @BotFather → ваш бот → Payments → Telegram Stars."
        )
        if "STARS" in (exc.message or "").upper():
            hint = f"Не удалось создать счёт: {exc.message}"
        await callback.answer(hint, show_alert=True)
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
    charge_id = payment.telegram_payment_charge_id or (
        f"stars_{message.from_user.id}_{payment.total_amount}_{message.message_id}"
    )

    activated = await user_service.activate_premium(
        user=user,
        charge_id=charge_id,
        amount=payment.total_amount,
        payload=payment.invoice_payload,
        is_subscription=is_subscription,
    )
    await session.flush()

    if not activated:
        if user_service.is_premium_active(user):
            until = user.premium_until.strftime("%d.%m.%Y") if user.premium_until else "—"
            await message.answer(
                f"ℹ️ Этот платёж уже был обработан ранее.\n"
                f"⭐ Premium активен до: <b>{until}</b>"
            )
        else:
            await message.answer(
                "⚠️ Не удалось активировать Premium по этому платежу.\n"
                "Напишите в поддержку или попробуйте /premium снова."
            )
        return

    until = user.premium_until.strftime("%d.%m.%Y") if user.premium_until else "—"
    await message.answer(
        "🎉 <b>Спасибо за Premium!</b>\n\n"
        f"⭐ Подписка активна до: <b>{until}</b>\n"
        "📖 Теперь вам доступен личный словарь: /dictionary\n\n"
        f"💝 Поддержать проект: {SUPPORT_URL}"
    )
