"""Unit tests for MH-42: Table Splitting and 2-Hour Cutoff Rule."""
import pytest
from datetime import date, time, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from server.database import Base, set_sqlite_pragma
from server.const import SlotStatus, ReservationStatus, UserRole
from server.models.DAO import UserDAO, TableDAO, TimeSlotDAO, SlotTableDAO, ReservationDAO
from server.models.DTO.reservation_dto import ReservationCreate
from server.service.booking_service import (
    create_reservation,
    validate_two_hour_rule,
    assign_tables_for_party,
)


@pytest.fixture
def split_test_db():
    """In-memory SQLite database setup for testing splitting and 2-hour rule."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    set_sqlite_pragma(engine.raw_connection(), None)
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine)
    session = TestingSession()

    # Users
    u1 = UserDAO(id=1, email="h1@test.com", password_hash="dummy", first_name="Hiker", last_name="One")
    u2 = UserDAO(id=2, email="h2@test.com", password_hash="dummy", first_name="Hiker", last_name="Two")
    u3 = UserDAO(id=3, email="h3@test.com", password_hash="dummy", first_name="Hiker", last_name="Three")

    # Tables: T1 (6 seats), T2 (4 seats), T3 (8 seats)
    t1 = TableDAO(id=1, table_number="T1", capacity=6, location="Indoor Main")
    t2 = TableDAO(id=2, table_number="T2", capacity=4, location="Indoor Small")
    t3 = TableDAO(id=3, table_number="T3", capacity=8, location="Indoor Large")

    # Slot at 12:00 on 2026-11-15
    slot = TimeSlotDAO(
        id=1,
        date=date(2026, 11, 15),
        start_time=time(12, 0),
        end_time=time(13, 0),
        meal_type="Lunch",
        status=SlotStatus.OPEN.value,
    )
    # Total capacity = 18
    st1 = SlotTableDAO(id=1, slot_id=1, table_id=1, available_seats=6)
    st2 = SlotTableDAO(id=2, slot_id=1, table_id=2, available_seats=4)
    st3 = SlotTableDAO(id=3, slot_id=1, table_id=3, available_seats=8)

    session.add_all([u1, u2, u3, t1, t2, t3, slot, st1, st2, st3])
    session.commit()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_two_hour_cutoff_rule(split_test_db):
    """Test MH-01 / MH-42: Hiker can reserve a seat up to 2 hours before the due time."""
    slot = split_test_db.query(TimeSlotDAO).filter_by(id=1).first()

    # Slot time is 2026-11-15 12:00 -> Cutoff is 2026-11-15 10:00

    # 1. Booking at 09:30 (2.5h before) -> OK
    validate_two_hour_rule(slot, current_time=datetime(2026, 11, 15, 9, 30))

    # 2. Booking at 10:00 (exactly 2h before) -> OK
    validate_two_hour_rule(slot, current_time=datetime(2026, 11, 15, 10, 0))

    # 3. Booking at 10:01 (1h 59m before) -> Rejected
    with pytest.raises(ValueError, match="at least 2 hours before"):
        validate_two_hour_rule(slot, current_time=datetime(2026, 11, 15, 10, 1))

    # 4. Booking after slot start -> Rejected
    with pytest.raises(ValueError, match="at least 2 hours before"):
        validate_two_hour_rule(slot, current_time=datetime(2026, 11, 15, 12, 15))


def test_two_hour_cutoff_in_create_reservation(split_test_db):
    """Test create_reservation enforces the 2-hour cutoff rule."""
    payload = ReservationCreate(
        slot_id=1,
        party_size=2,
        user_id=1,
        contact_name="Hiker One",
        contact_email="h1@test.com",
    )
    # Attempt booking 1 hour before due time
    late_time = datetime(2026, 11, 15, 11, 0)
    with pytest.raises(ValueError, match="at least 2 hours before"):
        create_reservation(split_test_db, payload, current_time=late_time)

    # Attempt booking 3 hours before due time -> Success
    valid_time = datetime(2026, 11, 15, 9, 0)
    res = create_reservation(split_test_db, payload, current_time=valid_time)
    assert res.id is not None
    assert res.status == ReservationStatus.CONFIRMED.value


def test_best_fit_single_table_allocation(split_test_db):
    """
    Test MH-01: Keep party together at one table using the smallest set of seats.
    T2 has 4 seats, T1 has 6 seats, T3 has 8 seats.
    Party of 4 should pick T2 (best fit), leaving T1 and T3 open.
    """
    slot = split_test_db.query(TimeSlotDAO).filter_by(id=1).first()
    allocations = assign_tables_for_party(slot, party_size=4)

    assert len(allocations) == 1
    slot_table, seats = allocations[0]
    assert slot_table.table.table_number == "T2"  # 4 seats exact fit
    assert seats == 4


def test_party_split_over_more_tables(split_test_db):
    """
    Test MH-01 & MH-42: When party size exceeds any single table,
    split party across minimum number of tables.
    Party of 11:
    Single tables: T3 (8), T1 (6), T2 (4). None can fit 11.
    System uses as few tables as possible: T3 (takes 8) + T1 (takes 3).
    """
    slot = split_test_db.query(TimeSlotDAO).filter_by(id=1).first()
    allocations = assign_tables_for_party(slot, party_size=11)

    # Must use 2 tables (not 3)
    assert len(allocations) == 2

    # First table takes 8 seats from largest table (T3)
    assert allocations[0][0].table.table_number == "T3"
    assert allocations[0][1] == 8

    # Second table takes remaining 3 seats from next largest table (T1)
    assert allocations[1][0].table.table_number == "T1"
    assert allocations[1][1] == 3

    # Total seats equals party size
    assert sum(seats for _, seats in allocations) == 11


def test_full_split_reservation_lifecycle(split_test_db):
    """Full database lifecycle test for a split party booking."""
    payload = ReservationCreate(
        slot_id=1,
        party_size=12,
        user_id=2,
        contact_name="Group Leader",
        contact_email="leader@test.com",
        special_requirements="All outdoor gear",
    )
    valid_time = datetime(2026, 11, 15, 8, 0)
    res = create_reservation(split_test_db, payload, current_time=valid_time)

    assert res.id is not None
    assert res.party_size == 12
    # Verify split across 2 tables: T3 (8) + T1 (4)
    assert len(res.table_assignments) == 2

    assigned_numbers = {
        ta.slot_table.table.table_number: ta.assigned_seats
        for ta in res.table_assignments
    }
    assert assigned_numbers == {"T3": 8, "T1": 4}

    # Verify slot remaining capacity: 18 - 12 = 6
    slot = split_test_db.query(TimeSlotDAO).filter_by(id=1).first()
    assert slot.reserved_seats == 12
    assert slot.remaining_seats == 6
