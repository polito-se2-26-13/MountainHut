"""Unit tests for SQLAlchemy models and business constraints."""
import pytest
from datetime import date, time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from server.database import Base, set_sqlite_pragma
from server.const import UserRole, SlotStatus, ReservationStatus
from server.models.DAO import (
    UserDAO,
    HutInfoDAO,
    TableDAO,
    TimeSlotDAO,
    SlotTableDAO,
    ReservationDAO,
    ReservationTableAssignmentDAO,
)


@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    # Register sqlite pragma for foreign keys
    set_sqlite_pragma(engine.raw_connection(), None)
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_user_creation_and_password_hashing(db_session):
    """Test user creation, password verification, and helper properties."""
    user = UserDAO(
        email="guide@example.com",
        first_name="Marco",
        last_name="Rossi",
        phone="+39 333 1234567",
        role=UserRole.HIKER.value,
        notes="UIAGM Mountain Guide",
        emergency_contact="Anna Rossi (+39 333 7654321)",
    )
    user.set_password("GuideSecret123!")
    db_session.add(user)
    db_session.commit()

    assert user.id is not None
    assert user.full_name == "Marco Rossi"
    assert user.verify_password("GuideSecret123!") is True
    assert user.verify_password("WrongPassword") is False
    assert user.to_dict()["email"] == "guide@example.com"


def test_user_email_unique_constraint(db_session):
    """Test that email must be unique."""
    u1 = UserDAO(
        email="duplicate@example.com",
        password_hash="dummy",
        first_name="User",
        last_name="One",
    )
    u2 = UserDAO(
        email="duplicate@example.com",
        password_hash="dummy",
        first_name="User",
        last_name="Two",
    )
    db_session.add(u1)
    db_session.commit()

    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_hut_info(db_session):
    """Test creating and retrieving hut information."""
    hut = HutInfoDAO(
        name="Rifugio Alpe Grande",
        location="Valle d'Aosta",
        altitude_m=2150,
        has_ebike_charging=True,
    )
    db_session.add(hut)
    db_session.commit()

    saved = db_session.query(HutInfoDAO).first()
    assert saved.name == "Rifugio Alpe Grande"
    assert saved.altitude_m == 2150
    assert saved.has_ebike_charging is True


def test_slot_capacity_and_tables(db_session):
    """Test MH-02: define set of tables and seats available for each time slot."""
    # Create tables
    t1 = TableDAO(table_number="T1", capacity=6, location="Indoor")
    t2 = TableDAO(table_number="T2", capacity=4, location="Indoor")
    t3 = TableDAO(table_number="T3", capacity=6, location="Terrace")
    db_session.add_all([t1, t2, t3])
    db_session.commit()

    # Create slot (Lunch)
    slot = TimeSlotDAO(
        date=date(2026, 11, 1),
        start_time=time(12, 0),
        end_time=time(13, 0),
        meal_type="Lunch",
        status=SlotStatus.OPEN.value,
    )
    db_session.add(slot)
    db_session.commit()

    # Configure slot capacity: indoor tables + terrace
    st1 = SlotTableDAO(slot_id=slot.id, table_id=t1.id, available_seats=6)
    st2 = SlotTableDAO(slot_id=slot.id, table_id=t2.id, available_seats=4)
    st3 = SlotTableDAO(slot_id=slot.id, table_id=t3.id, available_seats=6)
    db_session.add_all([st1, st2, st3])
    db_session.commit()

    # Total capacity should be 16 seats
    assert slot.total_capacity == 16
    assert slot.remaining_seats == 16
    assert st1.free_seats == 6


def test_reservation_and_confirmation(db_session):
    """Test MH-01 & MH-03: table booking, table sharing, and confirmation details."""
    # 1. Setup user, table, and slot
    hiker = UserDAO(
        email="hiker@example.com",
        password_hash="dummy",
        first_name="Jane",
        last_name="Doe",
        phone="+39 340 5556677",
    )
    db_session.add(hiker)

    table = TableDAO(table_number="T1", capacity=6, location="Indoor Main Hall")
    db_session.add(table)
    db_session.commit()

    slot = TimeSlotDAO(
        date=date(2026, 11, 1),
        start_time=time(12, 0),
        end_time=time(13, 0),
        meal_type="Lunch",
    )
    db_session.add(slot)
    db_session.commit()

    slot_table = SlotTableDAO(slot_id=slot.id, table_id=table.id, available_seats=6)
    db_session.add(slot_table)
    db_session.commit()

    # 2. Hiker makes a reservation for 4 people
    res = ReservationDAO(
        booking_reference="MH-TEST-001",
        user_id=hiker.id,
        slot_id=slot.id,
        party_size=4,
        special_requirements="1 vegetarian meal, nut allergy",
        contact_name=hiker.full_name,
        contact_email=hiker.email,
        contact_phone=hiker.phone,
        status=ReservationStatus.CONFIRMED.value,
    )
    db_session.add(res)
    db_session.commit()

    # Assign 4 seats at table T1
    assignment = ReservationTableAssignmentDAO(
        reservation_id=res.id,
        slot_table_id=slot_table.id,
        assigned_seats=4,
    )
    db_session.add(assignment)
    db_session.commit()

    # Check slot remaining capacity: 6 - 4 = 2 seats remaining
    assert slot.reserved_seats == 4
    assert slot.remaining_seats == 2
    assert slot_table.occupied_seats == 4
    assert slot_table.free_seats == 2

    # Check confirmation details for MH-03
    conf = res.to_confirmation_dict()
    assert conf["bookingReference"] == "MH-TEST-001"
    assert conf["hikerName"] == "Jane Doe"
    assert conf["partySize"] == 4
    assert conf["specialRequirements"] == "1 vegetarian meal, nut allergy"
    assert conf["date"] == "2026-11-01"
    assert conf["timeSlot"] == "12:00 - 13:00"
    assert len(conf["assignedTables"]) == 1
    assert conf["assignedTables"][0]["tableNumber"] == "T1"
    assert conf["assignedTables"][0]["seatsAssigned"] == 4


def test_table_sharing_between_parties(db_session):
    """Test MH-01: Table sharing rule - two separate reservations sharing table T1."""
    # Setup users
    hiker1 = UserDAO(email="h1@test.com", password_hash="dummy", first_name="A", last_name="1")
    hiker2 = UserDAO(email="h2@test.com", password_hash="dummy", first_name="B", last_name="2")
    table = TableDAO(table_number="T1", capacity=6, location="Indoor")
    db_session.add_all([hiker1, hiker2, table])
    db_session.commit()

    slot = TimeSlotDAO(date=date(2026, 11, 2), start_time=time(13, 0), end_time=time(14, 0))
    db_session.add(slot)
    db_session.commit()

    st = SlotTableDAO(slot_id=slot.id, table_id=table.id, available_seats=6)
    db_session.add(st)
    db_session.commit()

    # Reservation 1: party of 4
    res1 = ReservationDAO(
        booking_reference="MH-SHARE-1",
        user_id=hiker1.id,
        slot_id=slot.id,
        party_size=4,
        contact_name="A 1",
        contact_email="h1@test.com",
    )
    db_session.add(res1)
    db_session.commit()
    db_session.add(ReservationTableAssignmentDAO(reservation_id=res1.id, slot_table_id=st.id, assigned_seats=4))
    db_session.commit()

    # Reservation 2: party of 2 shares table T1
    res2 = ReservationDAO(
        booking_reference="MH-SHARE-2",
        user_id=hiker2.id,
        slot_id=slot.id,
        party_size=2,
        contact_name="B 2",
        contact_email="h2@test.com",
    )
    db_session.add(res2)
    db_session.commit()
    db_session.add(ReservationTableAssignmentDAO(reservation_id=res2.id, slot_table_id=st.id, assigned_seats=2))
    db_session.commit()

    # Table is now full (4 + 2 = 6)
    assert st.occupied_seats == 6
    assert st.free_seats == 0
    assert slot.remaining_seats == 0


def test_party_split_across_tables(db_session):
    """Test MH-01: Party exceeds single table capacity and is split across multiple tables."""
    hiker = UserDAO(email="biggroup@test.com", password_hash="dummy", first_name="Leader", last_name="Group")
    t1 = TableDAO(table_number="T1", capacity=6, location="Indoor")
    t2 = TableDAO(table_number="T2", capacity=4, location="Indoor")
    db_session.add_all([hiker, t1, t2])
    db_session.commit()

    slot = TimeSlotDAO(date=date(2026, 11, 3), start_time=time(12, 0), end_time=time(13, 0))
    db_session.add(slot)
    db_session.commit()

    st1 = SlotTableDAO(slot_id=slot.id, table_id=t1.id, available_seats=6)
    st2 = SlotTableDAO(slot_id=slot.id, table_id=t2.id, available_seats=4)
    db_session.add_all([st1, st2])
    db_session.commit()

    # Group of 9 people: 6 at table T1 and 3 at table T2
    res = ReservationDAO(
        booking_reference="MH-SPLIT-01",
        user_id=hiker.id,
        slot_id=slot.id,
        party_size=9,
        contact_name="Leader Group",
        contact_email="biggroup@test.com",
    )
    db_session.add(res)
    db_session.commit()

    db_session.add_all([
        ReservationTableAssignmentDAO(reservation_id=res.id, slot_table_id=st1.id, assigned_seats=6),
        ReservationTableAssignmentDAO(reservation_id=res.id, slot_table_id=st2.id, assigned_seats=3),
    ])
    db_session.commit()

    assert slot.reserved_seats == 9
    assert slot.remaining_seats == 1  # 10 - 9
    assert st1.free_seats == 0
    assert st2.free_seats == 1


def test_unique_booking_per_slot_constraint(db_session):
    """Test MH-01 rule: only one booking per time slot on a date per hiker."""
    hiker = UserDAO(email="onebooking@test.com", password_hash="dummy", first_name="Hiker", last_name="X")
    db_session.add(hiker)
    slot = TimeSlotDAO(date=date(2026, 11, 4), start_time=time(12, 0), end_time=time(13, 0))
    db_session.add(slot)
    db_session.commit()

    # First booking succeeds
    res1 = ReservationDAO(
        booking_reference="MH-FIRST",
        user_id=hiker.id,
        slot_id=slot.id,
        party_size=2,
        contact_name="Hiker X",
        contact_email="onebooking@test.com",
    )
    db_session.add(res1)
    db_session.commit()

    # Second booking by the same hiker for the same slot should fail
    res2 = ReservationDAO(
        booking_reference="MH-SECOND",
        user_id=hiker.id,
        slot_id=slot.id,
        party_size=3,
        contact_name="Hiker X",
        contact_email="onebooking@test.com",
    )
    db_session.add(res2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

