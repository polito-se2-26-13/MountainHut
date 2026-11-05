# server/tests/test_booking_unit.py

"""Unit and service-level tests for MountainHut Booking Rules."""

import pytest
import pytest_asyncio

from datetime import date, time, datetime

from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from server.database import Base, set_sqlite_pragma
from server.const import SlotStatus, ReservationStatus,UserRole

from server.models.DAO.user import UserDAO
from server.models.DAO.table import TableDAO
from server.models.DAO.time_slot import TimeSlotDAO, SlotTableDAO
from server.models.DAO.reservation import ReservationDAO

from server.models.DTO.reservation_dto import ReservationCreate

from server.service.booking_service import (
    validate_two_hour_rule,
    assign_tables_for_party,
    create_reservation,
    get_slot_availability,
    get_reservation_by_reference,
    get_user_reservations,
)



# Test database fixture
@pytest_asyncio.fixture
async def booking_db():
    """Create an isolated in-memory database for booking tests."""

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

    # Create test users
    user1 = UserDAO(
        id=1,
        email="alice@test.com",
        password_hash="dummy",
        first_name="Alice",
        last_name="Walker",
        role=UserRole.HIKER.value,
    )

    user2 = UserDAO(
        id=2,
        email="bob@test.com",
        password_hash="dummy",
        first_name="Bob",
        last_name="Smith",
        role=UserRole.HIKER.value,
    )

    user3 = UserDAO(
        id=3,
        email="charlie@test.com",
        password_hash="dummy",
        first_name="Charlie",
        last_name="Brown",
        role=UserRole.HIKER.value,
    )

    # Create physical tables
    t1 = TableDAO(
        id=1,
        table_number="T1",
        capacity=6,
        location="Indoor",
    )

    t2 = TableDAO(
        id=2,
        table_number="T2",
        capacity=4,
        location="Indoor",
    )

    t3 = TableDAO(
        id=3,
        table_number="T3",
        capacity=8,
        location="Terrace",
    )

    # Future time slot, so normal bookings are not rejected
    # by the two-hour cutoff rule.
    slot = TimeSlotDAO(
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
    )

    st2 = SlotTableDAO(
        id=2,
        slot_id=1,
        table_id=2,
        available_seats=4,
    )

    st3 = SlotTableDAO(
        id=3,
        slot_id=1,
        table_id=3,
        available_seats=8,
    )

    async with TestingSession() as session:
        session.add_all([
            user1,
            user2,
            user3,
            t1,
            t2,
            t3,
            slot,
            st1,
            st2,
            st3,
        ])
        await session.commit()

    async with TestingSession() as session:
        yield session

    await engine.dispose()



# Helper function
def create_booking(
    user_id=1,
    slot_id=1,
    party_size=2,
):
    """Create a valid booking payload."""

    return ReservationCreate(
        slot_id=slot_id,
        party_size=party_size,
        user_id=user_id,
        contact_name="Alice Walker",
        contact_email="alice@test.com",
        contact_phone="+393401112233",
        special_requirements=None,
    )



# 1. Two-hour booking rule
def test_booking_allowed_more_than_two_hours_before():
    """Booking is allowed more than two hours before the slot."""

    slot = TimeSlotDAO(
        date=date(2030, 11, 15),
        start_time=time(12, 0),
        end_time=time(13, 0),
        status=SlotStatus.OPEN.value,
    )

    current_time = datetime(2030, 11, 15, 9, 0)

    validate_two_hour_rule(slot, current_time)


def test_booking_allowed_exactly_two_hours_before():
    """Booking is allowed exactly two hours before the slot."""

    slot = TimeSlotDAO(
        date=date(2030, 11, 15),
        start_time=time(12, 0),
        end_time=time(13, 0),
    )

    current_time = datetime(2030, 11, 15, 10, 0)

    validate_two_hour_rule(slot, current_time)


def test_booking_rejected_less_than_two_hours_before():
    """Booking is rejected less than two hours before the slot."""

    slot = TimeSlotDAO(
        date=date(2030, 11, 15),
        start_time=time(12, 0),
        end_time=time(13, 0),
    )

    current_time = datetime(2030, 11, 15, 10, 1)

    with pytest.raises(ValueError, match="at least 2 hours before"):
        validate_two_hour_rule(slot, current_time)


def test_booking_rejected_after_slot_starts():
    """Booking is rejected after the time slot has started."""

    slot = TimeSlotDAO(
        date=date(2030, 11, 15),
        start_time=time(12, 0),
        end_time=time(13, 0),
    )

    current_time = datetime(2030, 11, 15, 12, 15)

    with pytest.raises(ValueError, match="at least 2 hours before"):
        validate_two_hour_rule(slot, current_time)



# 2. Table assignment rules
def create_assignment_slot():
    """Create a transient slot with three available tables."""

    table1 = TableDAO(
        id=1,
        table_number="T1",
        capacity=6,
        location="Indoor",
    )

    table2 = TableDAO(
        id=2,
        table_number="T2",
        capacity=4,
        location="Indoor",
    )

    table3 = TableDAO(
        id=3,
        table_number="T3",
        capacity=8,
        location="Terrace",
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


def test_party_assigned_to_single_table():
    """A party is seated at one table if it can fit."""

    slot = create_assignment_slot()

    allocations = assign_tables_for_party(slot, party_size=4)

    assert len(allocations) == 1
    assert allocations[0][0].table.table_number == "T2"
    assert allocations[0][1] == 4


def test_best_fit_table_is_selected():
    """The smallest suitable table is selected."""

    slot = create_assignment_slot()

    allocations = assign_tables_for_party(slot, party_size=3)

    assert len(allocations) == 1
    assert allocations[0][0].table.table_number == "T2"
    assert allocations[0][1] == 3


def test_party_split_across_multiple_tables():
    """A large party is split when no single table can fit it."""

    slot = create_assignment_slot()

    allocations = assign_tables_for_party(slot, party_size=11)

    assert len(allocations) == 2

    assigned_seats = sum(seats for _, seats in allocations)

    assert assigned_seats == 11
    assert len({slot_table.id for slot_table, _ in allocations}) == len(allocations)
    for slot_table, seats in allocations:
        assert 0 < seats <= slot_table.free_seats

def test_party_uses_minimum_number_of_tables():
    """The minimum number of tables is selected."""

    slot = create_assignment_slot()

    allocations = assign_tables_for_party(slot, party_size=12)

    assert len(allocations) == 2
    assert sum(seats for _, seats in allocations) == 12


def test_unavailable_tables_are_not_selected():
    """Tables marked unavailable must not be used."""

    slot = create_assignment_slot()

    slot.slot_tables[0].is_available = False
    slot.slot_tables[1].is_available = False

    allocations = assign_tables_for_party(slot, party_size=5)

    assert len(allocations) == 1
    assert allocations[0][0].table.table_number == "T3"


def test_no_available_tables_rejected():
    """Booking allocation fails when no tables are available."""

    slot = create_assignment_slot()

    for slot_table in slot.slot_tables:
        slot_table.is_available = False

    with pytest.raises(ValueError, match="No available tables"):
        assign_tables_for_party(slot, party_size=2)


def test_insufficient_table_capacity_rejected():
    """Allocation fails when total free seats are insufficient."""

    slot = create_assignment_slot()

    with pytest.raises(ValueError, match="Not enough free seats"):
        assign_tables_for_party(slot, party_size=19)



# 3. Booking validation and creation
@pytest.mark.asyncio
async def test_create_reservation_successfully(booking_db):
    """A valid booking is successfully created."""

    payload = create_booking(
        user_id=1,
        slot_id=1,
        party_size=4,
    )

    reservation = await create_reservation(
        booking_db,
        payload,
        current_time=datetime(2030, 11, 15, 8, 0),
    )

    assert reservation.id is not None
    assert reservation.booking_reference.startswith("MH-")
    assert reservation.user_id == 1
    assert reservation.slot_id == 1
    assert reservation.party_size == 4
    assert reservation.status == ReservationStatus.CONFIRMED.value


@pytest.mark.asyncio
async def test_non_existing_user_rejected(booking_db):
    """A reservation cannot be created for a non-existing user."""

    payload = create_booking(user_id=999)

    with pytest.raises(ValueError, match="User with id 999 not found"):
        await create_reservation(
            booking_db,
            payload,
            current_time=datetime(2030, 11, 15, 8, 0),
        )


@pytest.mark.asyncio
async def test_non_existing_slot_rejected(booking_db):
    """A reservation cannot be created for a non-existing slot."""

    payload = create_booking(slot_id=999)

    with pytest.raises(ValueError, match="Time slot with id 999 not found"):
        await create_reservation(
            booking_db,
            payload,
            current_time=datetime(2030, 11, 15, 8, 0),
        )


@pytest.mark.asyncio
async def test_closed_slot_rejected(booking_db):
    """A closed slot cannot accept bookings."""

    slot = await booking_db.get(TimeSlotDAO, 1)
    slot.status = SlotStatus.CLOSED.value
    await booking_db.commit()

    payload = create_booking()

    with pytest.raises(ValueError, match="cannot accept reservations"):
        await create_reservation(
            booking_db,
            payload,
            current_time=datetime(2030, 11, 15, 8, 0),
        )


@pytest.mark.asyncio
async def test_cancelled_slot_rejected(booking_db):
    """A cancelled slot cannot accept bookings."""

    slot = await booking_db.get(TimeSlotDAO, 1)
    slot.status = SlotStatus.CANCELLED.value
    await booking_db.commit()

    payload = create_booking()

    with pytest.raises(ValueError, match="cannot accept reservations"):
        await create_reservation(
            booking_db,
            payload,
            current_time=datetime(2030, 11, 15, 8, 0),
        )


@pytest.mark.asyncio
async def test_duplicate_booking_rejected(booking_db):
    """A hiker cannot make two confirmed bookings for the same slot."""

    payload = create_booking(user_id=1, party_size=2)

    await create_reservation(
        booking_db,
        payload,
        current_time=datetime(2030, 11, 15, 8, 0),
    )

    with pytest.raises(
        ValueError,
        match="already has a confirmed booking",
    ):
        await create_reservation(
            booking_db,
            payload,
            current_time=datetime(2030, 11, 15, 8, 0),
        )


@pytest.mark.asyncio
async def test_different_users_can_book_same_slot(booking_db):
    """Different hikers can book the same slot if capacity remains."""

    first = await create_reservation(
        booking_db,
        create_booking(user_id=1, party_size=2),
        current_time=datetime(2030, 11, 15, 8, 0),
    )

    second = await create_reservation(
        booking_db,
        create_booking(user_id=2, party_size=3),
        current_time=datetime(2030, 11, 15, 8, 0),
    )

    assert first.id != second.id
    assert first.status == ReservationStatus.CONFIRMED.value
    assert second.status == ReservationStatus.CONFIRMED.value


@pytest.mark.asyncio
async def test_capacity_exceeded_rejected(booking_db):
    """A booking exceeding total remaining capacity is rejected."""

    payload = create_booking(
        user_id=1,
        party_size=19,
    )

    with pytest.raises(ValueError, match="Not enough seats available"):
        await create_reservation(
            booking_db,
            payload,
            current_time=datetime(2030, 11, 15, 8, 0),
        )



# 4. Slot availability and capacity deduction

@pytest.mark.asyncio
async def test_initial_slot_availability(booking_db):
    """Initial slot capacity is calculated correctly."""

    availability = await get_slot_availability(booking_db, 1)

    assert availability["total_capacity"] == 18
    assert availability["reserved_seats"] == 0
    assert availability["remaining_seats"] == 18


@pytest.mark.asyncio
async def test_capacity_deducted_after_booking(booking_db):
    """Confirmed bookings reduce remaining slot capacity."""

    await create_reservation(
        booking_db,
        create_booking(party_size=4),
        current_time=datetime(2030, 11, 15, 8, 0),
    )

    availability = await get_slot_availability(booking_db, 1)

    assert availability["total_capacity"] == 18
    assert availability["reserved_seats"] == 4
    assert availability["remaining_seats"] == 14


@pytest.mark.asyncio
async def test_unknown_slot_availability_rejected(booking_db):
    """Availability lookup fails for an unknown slot."""

    with pytest.raises(ValueError, match="Time slot with id 999 not found"):
        await get_slot_availability(booking_db, 999)



# 5. Reservation retrieval
@pytest.mark.asyncio
async def test_get_reservation_by_reference(booking_db):
    """A reservation can be retrieved using its booking reference."""

    created = await create_reservation(
        booking_db,
        create_booking(),
        current_time=datetime(2030, 11, 15, 8, 0),
    )

    found = await get_reservation_by_reference(
        booking_db,
        created.booking_reference,
    )

    assert found is not None
    assert found.id == created.id
    assert found.booking_reference == created.booking_reference


@pytest.mark.asyncio
async def test_unknown_booking_reference_returns_none(booking_db):
    """An unknown booking reference returns None."""

    result = await get_reservation_by_reference(
        booking_db,
        "UNKNOWN-REFERENCE",
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_user_reservations(booking_db):
    """All reservations belonging to a user are returned."""

    await create_reservation(
        booking_db,
        create_booking(user_id=1, party_size=2),
        current_time=datetime(2030, 11, 15, 8, 0),
    )

    reservations = await get_user_reservations(
        booking_db,
        user_id=1,
    )

    assert len(reservations) == 1
    assert reservations[0].user_id == 1
@pytest.mark.asyncio
async def test_booking_exactly_remaining_capacity_is_accepted(booking_db):
    """A booking equal to the remaining capacity is accepted."""
    await create_reservation(
        booking_db,
        create_booking(user_id=1, party_size=8),
        current_time=datetime(2030, 11, 15, 8, 0),
    )

    availability = await get_slot_availability(booking_db, 1)
    assert availability["remaining_seats"] == 10

    # Another user can book exactly the remaining 10 seats.
    reservation = await create_reservation(
        booking_db,
        create_booking(user_id=2, party_size=10),
        current_time=datetime(2030, 11, 15, 8, 0),
    )
    assert reservation.party_size == 10

    availability = await get_slot_availability(booking_db, 1)
    assert availability["remaining_seats"] == 0


@pytest.mark.asyncio
async def test_booking_one_seat_over_remaining_capacity_is_rejected(booking_db):
    """A booking one seat larger than the remaining capacity is rejected."""
    await create_reservation(
        booking_db,
        create_booking(user_id=1, party_size=17),
        current_time=datetime(2030, 11, 15, 8, 0),
    )

    with pytest.raises(ValueError, match="Not enough seats available"):
        await create_reservation(
            booking_db,
            create_booking(user_id=2, party_size=2),
            current_time=datetime(2030, 11, 15, 8, 0),
        )

    availability = await get_slot_availability(booking_db, 1)
    assert availability["remaining_seats"] == 1 