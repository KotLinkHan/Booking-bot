from datetime import date, timedelta

from aiogram.types import InlineKeyboardButton, KeyboardButton, ReplyKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services import SERVICES, SLOTS

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 Записатися")],
        [KeyboardButton(text="💈 Послуги та ціни")],
    ],
    resize_keyboard=True,
)


def with_cancel(kb: InlineKeyboardBuilder):
    kb.button(text="❌ Скасувати", callback_data="cancel")
    return kb


def services_kb():
    kb = InlineKeyboardBuilder()
    for key, (name, price) in SERVICES.items():
        kb.button(text=f"{name} - {price} грн", callback_data=f"svc:{key}")
    with_cancel(kb).adjust(1)
    return kb.as_markup()


def dates_kb(days=7):
    kb = InlineKeyboardBuilder()
    for i in range(days):
        d = date.today() + timedelta(days=i)
        kb.button(text=d.strftime("%d.%m"), callback_data=f"date:{d.isoformat()}")
    with_cancel(kb).adjust(4, 3, 1)
    return kb.as_markup()


def times_kb(taken=()):
    kb = InlineKeyboardBuilder()
    for t in SLOTS:
        if t not in taken:
            kb.button(text=t, callback_data=f"time:{t}")
    kb.adjust(3)
    kb.row(InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel"))
    return kb.as_markup()


def confirm_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Підтвердити", callback_data="confirm")
    with_cancel(kb).adjust(2)
    return kb.as_markup()