# server/tests/test_slot_unit.py

"""Unit and model-level tests for MountainHut Slot Rules (MH-38)."""

import pytest
import pytest_asyncio

from datetime import date, time

from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from server.database import Base, set_sqlite_pragma
from server.const import SlotStatus, ReservationStatus,UserRole

from server.models.DAO.user import UserDAO
from server.models.DAO.table import TableDAO
from server.models.DAO.time_slot import TimeSlotDAO, SlotTableDAO
from server.models.DAO.reservation import (
    ReservationDAO,
    ReservationTableAssignmentDAO,
)


# Test database fixture

@pytest_asyncio.fixture
async def slot_db():
    """Create an isolated in-memory database for slot tests."""

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

    # Create a hiker
    user = UserDAO(
        id=1,
        email="hiker@test.com",
        password_hash="dummy",
        first_name="Alice",
        last_name="Walker",
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
        location="Terrace",
    )

    # Create two time slots
    slot1 = TimeSlotDAO(
        id=1,
        date=date(2030, 11, 15),
        start_time=time(12, 0),
        end_time=time(13, 0),
        meal_type="Lunch",
        status=SlotStatus.OPEN.value,
    )

    slot2 = TimeSlotDAO(
        id=2,
        date=date(2030, 11, 15),
        start_time=time(19, 0),
        end_time=time(20, 30),
        meal_type="Dinner",
        status=SlotStatus.OPEN.value,
    )

    # Configure table capacity for slot 1
    st1 = SlotTableDAO(
        id=1,
        slot_id=1,
        table_id=1,
        available_seats=6,
        is_available=True,
    )

    st2 = SlotTableDAO(
        id=2,
        slot_id=1,
        table_id=2,
        available_seats=4,
        is_available=True,
    )
    st3 = SlotTableDAO(
        id=3,
        slot_id=2,
        table_id=2,
        available_seats=4,
        is_available=True,
    )
    # Confirmed reservation: 3 seats
    reservation1 = ReservationDAO(
        id=1,
        user_id=1,
        slot_id=1,
        party_size=3,
        contact_name="Alice Walker",
        contact_email="hiker@test.com",
        status=ReservationStatus.CONFIRMED.value,
    )

    # Cancelled reservation: 2 seats
    reservation2 = ReservationDAO(
        id=2,
        user_id=1,
        slot_id=2,
        party_size=2,
        contact_name="Alice Walker",
        contact_email="hiker@test.com",
        status=ReservationStatus.CANCELLED.value,
    )

    assignment1 = ReservationTableAssignmentDAO(
        id=1,
        reservation_id=1,
        slot_table_id=1,
        assigned_seats=3,
    )

    assignment2 = ReservationTableAssignmentDAO(
        id=2,
        reservation_id=2,
        slot_table_id=3,
        assigned_seats=2,
    )

    async with TestingSession() as session:
        # Step 1: Parent records
        session.add_all([
            user,
            t1,
            t2,
            slot1,
            slot2,
        ])
        await session.flush()

        # Step 2: Slot-table configurations
        session.add_all([
            st1,
            st2,
            st3,
        ])
        await session.flush()

        # Step 3: Reservations
        session.add_all([
            reservation1,
            reservation2,
        ])
        await session.flush()

        # Step 4: Reservation assignments
        session.add_all([
            assignment1,
            assignment2,
        ])
        await session.commit()

    async with TestingSession() as session:
        yield session

    await engine.dispose()



# 1. Time slot configuration
@pytest.mark.asyncio
async def test_create_time_slot(slot_db):
    """A time slot can be created with valid information."""

    slot = TimeSlotDAO(
        date=date(2030, 12, 1),
        start_time=time(12, 0),
        end_time=time(13, 0),
        meal_type="Lunch",
        status=SlotStatus.OPEN.value,
        notes="Lunch service",
    )

    slot_db.add(slot)
    await slot_db.commit()
    await slot_db.refresh(slot)

    assert slot.id is not None
    assert slot.date == date(2030, 12, 1)
    assert slot.start_time == time(12, 0)
    assert slot.end_time == time(13, 0)
    assert slot.meal_type == "Lunch"
    assert slot.status == SlotStatus.OPEN.value


@pytest.mark.asyncio
async def test_default_slot_status_is_open(slot_db):
    """A new time slot defaults to OPEN status."""

    slot = TimeSlotDAO(
        date=date(2030, 12, 2),
        start_time=time(12, 0),
        end_time=time(13, 0),
        meal_type="Lunch",
    )

    slot_db.add(slot)
    await slot_db.commit()
    await slot_db.refresh(slot)

    assert slot.status == SlotStatus.OPEN.value


@pytest.mark.asyncio
async def test_slot_status_can_be_updated(slot_db):
    """A slot status can be changed and persisted."""

    slot = await slot_db.get(TimeSlotDAO, 1)

    slot.status = SlotStatus.CLOSED.value

    await slot_db.commit()
    await slot_db.refresh(slot)

    assert slot.status == SlotStatus.CLOSED.value


@pytest.mark.asyncio
async def test_slot_can_be_cancelled(slot_db):
    """A slot can be marked as CANCELLED."""

    slot = await slot_db.get(TimeSlotDAO, 1)

    slot.status = SlotStatus.CANCELLED.value

    await slot_db.commit()
    await slot_db.refresh(slot)

    assert slot.status == SlotStatus.CANCELLED.value


# 2. Table and slot configuration (MH-02)
@pytest.mark.asyncio
async def test_multiple_tables_can_be_assigned_to_one_slot(slot_db):
    """Multiple physical tables can be configured for one slot."""

    slot_tables = (
        await slot_db.get(TimeSlotDAO, 1)
    ).slot_tables

    assert len(slot_tables) == 2

    table_ids = {item.table_id for item in slot_tables}

    assert table_ids == {1, 2}


@pytest.mark.asyncio
async def test_same_physical_table_can_be_used_in_different_slots(slot_db):
    """The same physical table can be configured for different slots."""

    new_assignment = SlotTableDAO(
        slot_id=2,
        table_id=1,
        available_seats=6,
        is_available=True,
    )

    slot_db.add(new_assignment)
    await slot_db.commit()

    saved = await slot_db.get(
        SlotTableDAO,
        new_assignment.id,
    )

    assert saved is not None
    assert saved.slot_id == 2
    assert saved.table_id == 1


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
async def test_slot_table_available_seats(slot_db):
    """Configured available seats are stored correctly."""

    slot_table = await slot_db.get(SlotTableDAO, 1)

    assert slot_table.available_seats == 6


@pytest.mark.asyncio
async def test_slot_table_default_availability(slot_db):
    """A new slot-table assignment defaults to available."""

    slot_table = SlotTableDAO(
        slot_id=2,
        table_id=1,
        available_seats=6,
    )

    slot_db.add(slot_table)
    await slot_db.commit()
    await slot_db.refresh(slot_table)

    assert slot_table.is_available is True


@pytest.mark.asyncio
async def test_unavailable_table_can_be_disabled(slot_db):
    """A table assignment can be marked as unavailable."""

    slot_table = await slot_db.get(SlotTableDAO, 1)

    slot_table.is_available = False

    await slot_db.commit()
    await slot_db.refresh(slot_table)

    assert slot_table.is_available is False

# 3. Slot capacity calculations
@pytest.mark.asyncio
async def test_total_slot_capacity(slot_db):
    """Total capacity is the sum of available table seats."""

    slot = await slot_db.get(TimeSlotDAO, 1)

    assert slot.total_capacity == 10


@pytest.mark.asyncio
async def test_unavailable_tables_excluded_from_total_capacity(slot_db):
    """Unavailable tables are excluded from total capacity."""

    slot = await slot_db.get(TimeSlotDAO, 1)

    slot_table = await slot_db.get(SlotTableDAO, 2)
    slot_table.is_available = False

    await slot_db.commit()

    assert slot.total_capacity == 6


@pytest.mark.asyncio
async def test_reserved_seats_count_confirmed_reservations(slot_db):
    """Only confirmed reservations contribute to reserved seats."""

    slot = await slot_db.get(TimeSlotDAO, 1)

    assert slot.reserved_seats == 3


@pytest.mark.asyncio
async def test_cancelled_reservations_not_counted(slot_db):
    """Cancelled reservations are not counted as reserved seats."""

    slot = await slot_db.get(TimeSlotDAO, 2)

    assert slot.reserved_seats == 0


@pytest.mark.asyncio
async def test_remaining_slot_capacity(slot_db):
    """Remaining capacity equals total capacity minus reserved seats."""

    slot = await slot_db.get(TimeSlotDAO, 1)

    assert slot.total_capacity == 10
    assert slot.reserved_seats == 3
    assert slot.remaining_seats == 7


@pytest.mark.asyncio
async def test_remaining_capacity_cannot_be_negative(slot_db):
    """Remaining capacity is never returned as a negative number."""

    slot = await slot_db.get(TimeSlotDAO, 1)

    # Simulate confirmed reservations exceeding configured capacity.
    slot.reservations.append(
        ReservationDAO(
            id=3,
            user_id=1,
            slot_id=1,
            party_size=20,
            contact_name="Extra Booking",
            contact_email="extra@test.com",
            status=ReservationStatus.CONFIRMED.value,
        )
    )

    assert slot.remaining_seats == 0



# 4. Slot table occupancy

@pytest.mark.asyncio
async def test_slot_table_occupied_seats(slot_db):
    """Occupied seats are calculated from confirmed assignments."""

    slot_table = await slot_db.get(SlotTableDAO, 1)

    assert slot_table.occupied_seats == 3


@pytest.mark.asyncio
async def test_slot_table_free_seats(slot_db):
    """Free seats equal configured seats minus occupied seats."""

    slot_table = await slot_db.get(SlotTableDAO, 1)

    assert slot_table.available_seats == 6
    assert slot_table.occupied_seats == 3
    assert slot_table.free_seats == 3


@pytest.mark.asyncio
async def test_cancelled_assignment_does_not_occupy_seats(slot_db):
    """Assignments linked to cancelled reservations do not occupy seats."""

    slot_table = await slot_db.get(SlotTableDAO, 3)

    assert slot_table.occupied_seats == 0
    assert slot_table.free_seats == 4



# 5. Slot data representation

@pytest.mark.asyncio
async def test_time_slot_to_dict(slot_db):
    """TimeSlotDAO.to_dict returns the expected slot information."""

    slot = await slot_db.get(TimeSlotDAO, 1)

    data = slot.to_dict()

    assert data["id"] == 1
    assert data["date"] == "2030-11-15"
    assert data["startTime"] == "12:00"
    assert data["endTime"] == "13:00"
    assert data["mealType"] == "Lunch"
    assert data["status"] == SlotStatus.OPEN.value

    assert data["totalCapacity"] == 10
    assert data["reservedSeats"] == 3
    assert data["remainingSeats"] == 7


@pytest.mark.asyncio
async def test_slot_table_to_dict(slot_db):
    """SlotTableDAO.to_dict returns the expected table information."""

    slot_table = await slot_db.get(SlotTableDAO, 1)

    data = slot_table.to_dict()

    assert data["id"] == 1
    assert data["slotId"] == 1
    assert data["tableId"] == 1
    assert data["tableNumber"] == "T1"
    assert data["tableLocation"] == "Indoor"

    assert data["availableSeats"] == 6
    assert data["occupiedSeats"] == 3
    assert data["freeSeats"] == 3
    assert data["isAvailable"] is True


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


@pytest.mark.asyncio
async def test_slot_table_configuration_is_scoped_to_its_slot(slot_db):
    """The cancelled reservation's assignment points to a slot-2 table."""
    reservation = await slot_db.get(ReservationDAO, 2)
    assignment = await slot_db.get(ReservationTableAssignmentDAO, 2)
    slot_table = await slot_db.get(SlotTableDAO, assignment.slot_table_id)

    assert reservation.slot_id == 2
    assert slot_table.slot_id == reservation.slot_id