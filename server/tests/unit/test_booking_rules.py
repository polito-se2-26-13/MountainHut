"""Booking rules that no other test checks.

The two-hour rule, best fit, splitting, closed slots, one booking per hiker and the
availability counts are tested in test_table_splitting.py, test_booking_service.py
and integration/test_booking.py. This file keeps the cases they do not reach:
tables that are not available, a cancelled slot and the remaining seats of a slot
that already has a booking.
"""

from datetime import date, time, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from server.controllers.reservation_controller import ReservationController
from server.database import (
    AsyncSessionLocal,
    Base,
    engine as real_engine,
    set_sqlite_pragma,
)
from server.models.DAO import (
    SlotTableDAO,
    TableDAO,
    TimeSlotDAO,
    UserDAO,
)
from server.models.DTO.reservation_dto import ReservationCreate
from server.models.enum.slot_status import SlotStatus
from server.models.enum.user_type import UserType
from server.models.error.conflict_error import ConflictError
from server.repositories.reservation_repository import ReservationRepository
from server.service.booking_service import assign_tables_for_party


# ---------------------------------------------------------------------------
# Test database
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def booking_db():
    """Create an isolated in-memory database for booking tests."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
    )
    event.listen(test_engine.sync_engine, "connect", set_sqlite_pragma)

    async with test_engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    TestingSession = async_sessionmaker(
        test_engine,
        expire_on_commit=False,
    )

    user1 = UserDAO(
        id=1,
        email="alice@test.com",
        password_hash="dummy",
        first_name="Alice",
        last_name="Walker",
        phone="+39 340 1112233",
        role=UserType.HIKER.value,
    )
    user2 = UserDAO(
        id=2,
        email="bob@test.com",
        password_hash="dummy",
        first_name="Bob",
        last_name="Smith",
        phone="+39 340 2223344",
        role=UserType.HIKER.value,
    )

    table1 = TableDAO(
        id=1, table_number="T1", capacity=6, location="Indoor"
    )
    table2 = TableDAO(
        id=2, table_number="T2", capacity=4, location="Indoor"
    )
    table3 = TableDAO(
        id=3, table_number="T3", capacity=8, location="Terrace"
    )

    slot = TimeSlotDAO(
        id=1,
        date=date.today() + timedelta(days=7),
        start_time=time(12, 0),
        end_time=time(13, 0),
        meal_type="Lunch",
        status=SlotStatus.OPEN.value,
    )

    slot_table1 = SlotTableDAO(
        id=1, slot_id=1, table_id=1, available_seats=6
    )
    slot_table2 = SlotTableDAO(
        id=2, slot_id=1, table_id=2, available_seats=4
    )
    slot_table3 = SlotTableDAO(
        id=3, slot_id=1, table_id=3, available_seats=8
    )

    async with TestingSession() as seed_session:
        seed_session.add_all([
            user1, user2,
            table1, table2, table3,
            slot,
            slot_table1, slot_table2, slot_table3,
        ])
        await seed_session.commit()

    # The controller/repository create their own sessions through this factory.
    AsyncSessionLocal.configure(bind=test_engine)

    async with TestingSession() as session:
        yield session

    AsyncSessionLocal.configure(bind=real_engine)
    await test_engine.dispose()


def create_booking(
    user_id=1,
    slot_id=1,
    party_size=2,
):
    """Create a valid reservation payload."""
    return ReservationCreate(
        slot_id=slot_id,
        party_size=party_size,
        user_id=user_id,
        contact_name="Alice Walker",
        contact_email="alice@test.com",
        contact_phone="+39 340 1112233",
        special_requirements=[],
    )


# ---------------------------------------------------------------------------
# 1. Tables that are not available
# ---------------------------------------------------------------------------

def create_assignment_slot():
    """Create a transient slot with three available tables."""
    table1 = TableDAO(
        id=1, table_number="T1", capacity=6, location="Indoor"
    )
    table2 = TableDAO(
        id=2, table_number="T2", capacity=4, location="Indoor"
    )
    table3 = TableDAO(
        id=3, table_number="T3", capacity=8, location="Terrace"
    )

    slot = TimeSlotDAO(
        date=date(2030, 11, 15),
        start_time=time(12, 0),
        end_time=time(13, 0),
        status=SlotStatus.OPEN.value,
    )
    slot.slot_tables = [
        SlotTableDAO(
            id=1,
            table_id=1,
            available_seats=6,
            is_available=True,
            table=table1,
            assignments=[],
        ),
        SlotTableDAO(
            id=2,
            table_id=2,
            available_seats=4,
            is_available=True,
            table=table2,
            assignments=[],
        ),
        SlotTableDAO(
            id=3,
            table_id=3,
            available_seats=8,
            is_available=True,
            table=table3,
            assignments=[],
        ),
    ]
    return slot


def test_unavailable_tables_are_not_selected():
    slot = create_assignment_slot()
    slot.slot_tables[0].is_available = False
    slot.slot_tables[1].is_available = False

    allocations = assign_tables_for_party(slot, party_size=5)

    assert len(allocations) == 1
    assert allocations[0][0].table.table_number == "T3"


def test_no_available_tables_rejected():
    slot = create_assignment_slot()
    for slot_table in slot.slot_tables:
        slot_table.is_available = False

    with pytest.raises(
        ConflictError,
        match="No available tables",
    ):
        assign_tables_for_party(slot, party_size=2)


# ---------------------------------------------------------------------------
# 2. A cancelled slot cannot be booked
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancelled_slot_rejected(booking_db):
    slot = (
        await booking_db.execute(
            select(TimeSlotDAO).where(TimeSlotDAO.id == 1)
        )
    ).scalar_one()
    slot.status = SlotStatus.CANCELLED.value
    await booking_db.commit()

    with pytest.raises(
        ConflictError,
        match="time slot is not open",
    ):
        await ReservationController().create_reservation(
            create_booking()
        )


# ---------------------------------------------------------------------------
# 3. Remaining seats of a slot that already has a booking
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_booking_exactly_remaining_capacity_is_accepted(booking_db):
    await ReservationController().create_reservation(
        create_booking(user_id=1, party_size=8)
    )

    availability = await ReservationRepository().get_slot_availability(1)
    assert availability["remaining_seats"] == 10

    reservation = await ReservationController().create_reservation(
        create_booking(user_id=2, party_size=10)
    )
    assert reservation.party_size == 10

    availability = await ReservationRepository().get_slot_availability(1)
    assert availability["remaining_seats"] == 0


@pytest.mark.asyncio
async def test_booking_one_seat_over_remaining_capacity_is_rejected(
    booking_db,
):
    await ReservationController().create_reservation(
        create_booking(user_id=1, party_size=17)
    )

    with pytest.raises(
        ConflictError,
        match="Not enough seats available",
    ):
        await ReservationController().create_reservation(
            create_booking(user_id=2, party_size=2)
        )

    availability = await ReservationRepository().get_slot_availability(1)
    assert availability["remaining_seats"] == 1
