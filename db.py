from datetime import date, datetime, timedelta

from sqlalchemy import UniqueConstraint, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

import os
from dotenv import load_dotenv

load_dotenv()

engine = create_async_engine(
    os.getenv("DATABASE_URL"),
    connect_args={"ssl": False},
)

Session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (UniqueConstraint("day", "slot"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    user_name: Mapped[str]
    service: Mapped[str]
    day: Mapped[date]
    slot: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)
    reminded: Mapped[bool] = mapped_column(default=False)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def taken_slots(day: date) -> set[str]:
    async with Session() as session:
        rows = await session.scalars(
            select(Appointment.slot).where(Appointment.day == day)
        )
        return set(rows)


async def add_appointment(user_id, user_name, service, day, slot) -> bool:
    async with Session() as session:
        session.add(Appointment(
            user_id=user_id, user_name=user_name,
            service=service, day=day, slot=slot,
        ))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
            return False
    return True

REMIND_BEFORE = timedelta(hours=2)


async def appointments_for(day: date) -> list[Appointment]:
    async with Session() as session:
        rows = await session.scalars(
            select(Appointment)
            .where(Appointment.day == day)
            .order_by(Appointment.slot)
        )
        return list(rows)


async def pending_reminders() -> list[Appointment]:
    now = datetime.now()
    async with Session() as session:
        rows = await session.scalars(
            select(Appointment).where(
                Appointment.reminded.is_(False),
                Appointment.day >= now.date(),
                Appointment.day <= now.date() + timedelta(days=1),
            )
        )
        due = []
        for a in rows:
            hour = datetime.strptime(a.slot, "%H:%M").time()
            left = datetime.combine(a.day, hour) - now
            if timedelta(0) < left <= REMIND_BEFORE:
                due.append(a)
        return due


async def mark_reminded(appointment_id: int):
    async with Session() as session:
        appointment = await session.get(Appointment, appointment_id)
        appointment.reminded = True
        await session.commit()