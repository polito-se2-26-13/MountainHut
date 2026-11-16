"""Unit and service-level tests for MountainHut booking rules.

The booking service currently exposes only the two pure business functions:
- validate_two_hour_rule
- assign_tables_for_party

Reservation creation and availability are tested through the controller/repository,
which are the interfaces used by the application.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

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
from server.models.enum.reservation_status import ReservationStatus
from server.models.enum.slot_status import SlotStatus
from server.models.enum.user_type import UserType
from server.models.error.conflict_error import ConflictError
from server.models.error.notfound_error import NotFoundError
from server.repositories.reservation_repository import ReservationRepository
from server.service.booking_service import (
    assign_tables_for_party,
    validate_two_hour_rule,
)

ITALY_TZ = ZoneInfo("Europe/Rome")


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
    user3 = UserDAO(
        id=3,
        email="charlie@test.com",
        password_hash="dummy",
        first_name="Charlie",
        last_name="Brown",
        phone="+39 340 3334455",
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
            user1, user2, user3,
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
        special_requirements=None,
    )


# ---------------------------------------------------------------------------
# 1. Two-hour booking rule
# ---------------------------------------------------------------------------

def create_rule_test_slot():
    return TimeSlotDAO(
        date=date(2030, 11, 15),
        start_time=time(12, 0),
        end_time=time(13, 0),
        status=SlotStatus.OPEN.value,
    )


def test_booking_allowed_more_than_two_hours_before():
    slot = create_rule_test_slot()
    current_time = datetime(2030, 11, 15, 9, 0, tzinfo=ITALY_TZ)

    validate_two_hour_rule(slot, current_time)


def test_booking_allowed_exactly_two_hours_before():
    slot = create_rule_test_slot()
    current_time = datetime(2030, 11, 15, 10, 0, tzinfo=ITALY_TZ)

    validate_two_hour_rule(slot, current_time)


def test_booking_rejected_less_than_two_hours_before():
    slot = create_rule_test_slot()
    current_time = datetime(
        2030, 11, 15, 10, 1, tzinfo=ITALY_TZ
    )

    with pytest.raises(
        ConflictError,
        match="at least 2 hours before",
    ):
        validate_two_hour_rule(slot, current_time)


def test_booking_rejected_after_slot_starts():
    slot = create_rule_test_slot()
    current_time = datetime(
        2030, 11, 15, 12, 15, tzinfo=ITALY_TZ
    )

    with pytest.raises(
        ConflictError,
        match="at least 2 hours before",
    ):
        validate_two_hour_rule(slot, current_time)


# ---------------------------------------------------------------------------
# 2. Table assignment rules
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


def test_party_assigned_to_single_table():
    slot = create_assignment_slot()

    allocations = assign_tables_for_party(slot, party_size=4)

    assert len(allocations) == 1
    assert allocations[0][0].table.table_number == "T2"
    assert allocations[0][1] == 4


def test_best_fit_table_is_selected():
    slot = create_assignment_slot()

    allocations = assign_tables_for_party(slot, party_size=3)

    assert len(allocations) == 1
    assert allocations[0][0].table.table_number == "T2"
    assert allocations[0][1] == 3


def test_party_split_across_multiple_tables():
    slot = create_assignment_slot()

    allocations = assign_tables_for_party(slot, party_size=11)

    assert len(allocations) == 2
    assert sum(seats for _, seats in allocations) == 11
    assert len({st.id for st, _ in allocations}) == len(allocations)
    for slot_table, seats in allocations:
        assert 0 < seats <= slot_table.free_seats


def test_party_uses_minimum_number_of_tables():
    slot = create_assignment_slot()

    allocations = assign_tables_for_party(slot, party_size=12)

    assert len(allocations) == 2
    assert sum(seats for _, seats in allocations) == 12


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


def test_insufficient_table_capacity_rejected():
    slot = create_assignment_slot()

    with pytest.raises(
        ConflictError,
        match="Not enough free seats",
    ):
        assign_tables_for_party(slot, party_size=19)


# ---------------------------------------------------------------------------
# 3. Reservation creation and validation through the controller
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_reservation_successfully(booking_db):
    payload = create_booking(user_id=1, party_size=4)

    reservation = await ReservationController().create_reservation(payload)

    assert reservation.id is not None
    assert reservation.booking_reference.startswith("MH-")
    assert reservation.user_id == 1
    assert reservation.slot_id == 1
    assert reservation.party_size == 4
    assert reservation.status == ReservationStatus.CONFIRMED.value
    assert len(reservation.assigned_tables) >= 1


@pytest.mark.asyncio
async def test_capacity_exceeded_rejected(booking_db):
    payload = create_booking(user_id=1, party_size=19)

    with pytest.raises(
        ConflictError,
        match="Not enough seats available",
    ):
        await ReservationController().create_reservation(payload)


@pytest.mark.asyncio
async def test_closed_slot_rejected(booking_db):
    slot = (
        await booking_db.execute(
            select(TimeSlotDAO).where(TimeSlotDAO.id == 1)
        )
    ).scalar_one()
    slot.status = SlotStatus.CLOSED.value
    await booking_db.commit()

    with pytest.raises(
        ConflictError,
        match="time slot is not open",
    ):
        await ReservationController().create_reservation(
            create_booking()
        )


@pytest.mark.asyncio
async def test_cancelled_slot_rejected(booking_db):
    slot = (
        await booking_db.execute(
            select(TimeSlotDAO).where(TimeSlotDAO.id == 1)
        )
    ).scalar_one()
    slot.status = SlotStatus.CANCELLED.value
    await booking_db.commit()

    with pytest.raises(ConflictError):
        await ReservationController().create_reservation(
            create_booking()
        )


@pytest.mark.asyncio
async def test_duplicate_booking_rejected(booking_db):
    payload = create_booking(user_id=1, party_size=2)

    await ReservationController().create_reservation(payload)

    with pytest.raises(
        ConflictError,
        match="already has a confirmed booking",
    ):
        await ReservationController().create_reservation(payload)


@pytest.mark.asyncio
async def test_different_users_can_book_same_slot(booking_db):
    first = await ReservationController().create_reservation(
        create_booking(user_id=1, party_size=2)
    )
    second = await ReservationController().create_reservation(
        create_booking(user_id=2, party_size=3)
    )

    assert first.id != second.id
    assert first.status == ReservationStatus.CONFIRMED.value
    assert second.status == ReservationStatus.CONFIRMED.value


# ---------------------------------------------------------------------------
# 4. Slot availability and capacity deduction through the repository
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_initial_slot_availability(booking_db):
    availability = await ReservationRepository().get_slot_availability(1)

    assert availability["total_capacity"] == 18
    assert availability["reserved_seats"] == 0
    assert availability["remaining_seats"] == 18


@pytest.mark.asyncio
async def test_capacity_deducted_after_booking(booking_db):
    await ReservationController().create_reservation(
        create_booking(party_size=4)
    )

    availability = await ReservationRepository().get_slot_availability(1)

    assert availability["total_capacity"] == 18
    assert availability["reserved_seats"] == 4
    assert availability["remaining_seats"] == 14


@pytest.mark.asyncio
async def test_unknown_slot_availability_rejected(booking_db):
    with pytest.raises(NotFoundError):
        await ReservationRepository().get_slot_availability(999)


# ---------------------------------------------------------------------------
# 5. Capacity boundary checks
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

