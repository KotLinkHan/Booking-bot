import asyncio
import logging

from aiogram import Bot

from db import mark_reminded, pending_reminders
from services import SERVICES


async def reminder_loop(bot: Bot):
    while True:
        try:
            for a in await pending_reminders():
                service = SERVICES[a.service][0].lower()
                try:
                    await bot.send_message(
                        a.user_id,
                        f"⏰ Нагадуємо: {a.day:%d.%m} о {a.slot} у вас {service}.",
                    )
                except Exception:
                    logging.exception("can't remind user %s", a.user_id)
                await mark_reminded(a.id)
        except Exception:
            logging.exception("reminder loop error")
        await asyncio.sleep(60)