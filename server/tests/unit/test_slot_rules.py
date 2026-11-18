"""Database rules of the slot tables (MH-02, MH-38).

Seats, capacity and free seats of a slot are tested in test_models.py and through
the API in integration/test_slots.py and integration/test_booking.py. This file
keeps what no other test checks: a table is used only once in a slot, and a slot
table needs a slot and a table that exist.
"""

import pytest
import pytest_asyncio

from datetime import date, time

from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from server.database import Base, set_sqlite_pragma
from server.models.enum.slot_status import SlotStatus

from server.models.DAO.table import TableDAO
from server.models.DAO.time_slot import TimeSlotDAO, SlotTableDAO


# Test database fixture

@pytest_asyncio.fixture
async def slot_db():
    """Create an isolated in-memory database with one slot using table T1."""

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )

    event.listen(engine.sync_engine, "connect", set_sqlite_pragma)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    TestingSession = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    t1 = TableDAO(
        id=1,
        table_number="T1",
        capacity=6,
        location="Indoor",
    )

    slot1 = TimeSlotDAO(
        id=1,
        date=date(2030, 11, 15),
        start_time=time(12, 0),
        end_time=time(13, 0),
        meal_type="Lunch",
        status=SlotStatus.OPEN.value,
    )

    st1 = SlotTableDAO(
        id=1,
        slot_id=1,
        table_id=1,
        available_seats=6,
        is_available=True,
    )

    async with TestingSession() as session:
        session.add_all([t1, slot1])
        await session.flush()
        session.add(st1)
        await session.commit()

    async with TestingSession() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_duplicate_table_assignment_in_same_slot_rejected(slot_db):
    """The same table cannot be assigned twice to the same slot."""

    duplicate = SlotTableDAO(
        slot_id=1,
        table_id=1,
        available_seats=6,
        is_available=True,
    )

    slot_db.add(duplicate)

    with pytest.raises(IntegrityError):
        await slot_db.commit()

    await slot_db.rollback()


@pytest.mark.asyncio
async def test_slot_table_cannot_reference_unknown_slot(slot_db):
    """A slot-table configuration must reference an existing time slot."""
    invalid_assignment = SlotTableDAO(
        slot_id=999,
        table_id=1,
        available_seats=6,
        is_available=True,
    )
    slot_db.add(invalid_assignment)

    with pytest.raises(IntegrityError):
        await slot_db.commit()

    await slot_db.rollback()


@pytest.mark.asyncio
async def test_slot_table_cannot_reference_unknown_table(slot_db):
    """A slot-table configuration must reference an existing physical table."""
    invalid_assignment = SlotTableDAO(
        slot_id=1,
        table_id=999,
        available_seats=6,
        is_available=True,
    )
    slot_db.add(invalid_assignment)

    with pytest.raises(IntegrityError):
        await slot_db.commit()

    await slot_db.rollback()
