import logging
from datetime import date

import os
from aiogram.filters import Command, CommandStart
from db import add_appointment, appointments_for, taken_slots

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from db import add_appointment, taken_slots

import keyboards as kb
from services import SERVICES, SLOTS
from states import Booking


router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Привіт! Я бот для запису.",
                         reply_markup=kb.main_menu)


@router.message(F.text == "💈 Послуги та ціни")
async def show_prices(message: Message):
    lines = [f"{name}: {price} грн" for name, price in SERVICES.values()]
    await message.answer("\n".join(lines))


@router.message(F.text == "📅 Записатися")
async def begin_booking(message: Message, state: FSMContext):
    await state.set_state(Booking.service)
    await message.answer("Оберіть послугу:", reply_markup=kb.services_kb())


@router.callback_query(Booking.service, F.data.startswith("svc:"))
async def pick_service(call: CallbackQuery, state: FSMContext):
    await state.update_data(service=call.data.split(":")[1])
    await state.set_state(Booking.date)
    await call.message.edit_text("Оберіть дату:", reply_markup=kb.dates_kb())
    await call.answer()


@router.callback_query(Booking.date, F.data.startswith("date:"))
async def pick_date(call: CallbackQuery, state: FSMContext):
    chosen = call.data.split(":", 1)[1]
    taken = await taken_slots(date.fromisoformat(chosen))

    if len(taken) >= len(SLOTS):
        await call.answer("На цей день усе зайнято", show_alert=True)
        return

    await state.update_data(date=chosen)
    await state.set_state(Booking.time)
    await call.message.edit_text("Оберіть час:", reply_markup=kb.times_kb(taken))
    await call.answer()


@router.callback_query(Booking.time, F.data.startswith("time:"))
async def pick_time(call: CallbackQuery, state: FSMContext):
    await state.update_data(time=call.data.split(":", 1)[1])
    await state.set_state(Booking.confirm)

    data = await state.get_data()
    name, price = SERVICES[data["service"]]
    day = date.fromisoformat(data["date"]).strftime("%d.%m.%Y")

    text = f"Перевірте запис:\n\n💈 {name} ({price} грн)\n📅 {day}\n🕒 {data['time']}"
    await call.message.edit_text(text, reply_markup=kb.confirm_kb())
    await call.answer()


@router.callback_query(Booking.confirm, F.data == "confirm")
async def confirm_booking(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    day = date.fromisoformat(data["date"])

    saved = await add_appointment(
        call.from_user.id, call.from_user.full_name,
        data["service"], day, data["time"],
    )

    if not saved:
        taken = await taken_slots(day)
        await state.set_state(Booking.time)
        await call.message.edit_text(
            "Цей час щойно зайняли. Оберіть інший:",
            reply_markup=kb.times_kb(taken),
        )
        await call.answer()
        return

    admin_id = os.getenv("ADMIN_ID")
    if admin_id:
        name = SERVICES[data["service"]][0]
        await call.bot.send_message(
            int(admin_id),
            f"🆕 Новий запис\n{call.from_user.full_name}\n"
            f"{name}, {day:%d.%m} о {data['time']}",
        )

    await state.clear()
    await call.message.edit_text("✅ Ви записані! Чекаємо на вас.")
    await call.answer()


@router.callback_query(F.data == "cancel")
async def cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("Запис скасовано.")
    await call.answer()

@router.message(Command("today"))
async def today(message: Message):
    if message.from_user.id != int(os.getenv("ADMIN_ID", 0)):
        return

    rows = await appointments_for(date.today())
    if not rows:
        await message.answer("На сьогодні записів немає.")
        return

    lines = [f"{a.slot} - {SERVICES[a.service][0]}, {a.user_name}" for a in rows]
    await message.answer("\n".join(lines))