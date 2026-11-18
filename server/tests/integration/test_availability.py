"""Integration & E2E tests for MountainHut Slot Availability (MH-04)."""

from datetime import date, time, timedelta

from server.models.DAO import (
    ReservationDAO,
    ReservationTableAssignmentDAO,
    SlotTableDAO,
    TableDAO,
    TimeSlotDAO,
    UserDAO,
)
from server.models.enum.reservation_status import ReservationStatus
from server.models.enum.slot_status import SlotStatus
from server.models.enum.user_type import UserType
from server.service.auth_service import generate_token


def seed_availability_data(db):
    """Create users, slots, tables, and one confirmed reservation."""
    future_date = date.today() + timedelta(days=7)

    alice = UserDAO(
        id=1,
        email="alice@test.com",
        password_hash="dummy",
        first_name="Alice",
        last_name="Walker",
        phone="+39 340 1112233",
        role=UserType.HIKER.value,
    )
    bob = UserDAO(
        id=2,
        email="bob@test.com",
        password_hash="dummy",
        first_name="Bob",
        last_name="Brown",
        phone="+39 340 4445566",
        role=UserType.HIKER.value,
    )

    table1 = TableDAO(
        id=1,
        table_number="T1",
        capacity=6,
        location="Main Hall",
    )
    table2 = TableDAO(
        id=2,
        table_number="T2",
        capacity=4,
        location="Main Hall",
    )
    table3 = TableDAO(
        id=3,
        table_number="T3",
        capacity=2,
        location="Terrace",
    )

    open_slot = TimeSlotDAO(
        id=1,
        date=future_date,
        start_time=time(12, 0),
        end_time=time(13, 0),
        meal_type="Lunch",
        status=SlotStatus.OPEN.value,
    )
    closed_slot = TimeSlotDAO(
        id=2,
        date=future_date,
        start_time=time(19, 0),
        end_time=time(20, 30),
        meal_type="Dinner",
        status=SlotStatus.CLOSED.value,
    )

    slot_tables = [
        SlotTableDAO(
            id=1,
            slot_id=1,
            table_id=1,
            available_seats=6,
            is_available=True,
        ),
        SlotTableDAO(
            id=2,
            slot_id=1,
            table_id=2,
            available_seats=4,
            is_available=True,
        ),
        SlotTableDAO(
            id=3,
            slot_id=1,
            table_id=3,
            available_seats=2,
            is_available=True,
        ),
        SlotTableDAO(
            id=4,
            slot_id=2,
            table_id=1,
            available_seats=6,
            is_available=True,
        ),
    ]

    # Existing confirmed booking: T1=4, T2=1, T3=1 occupied.
    reservation = ReservationDAO(
        id=1,
        booking_reference="MH-INIT-001",
        user_id=2,
        slot_id=1,
        party_size=6,
        contact_name="Bob Brown",
        contact_email="bob@test.com",
        status=ReservationStatus.CONFIRMED.value,
    )
    assignments = [
        ReservationTableAssignmentDAO(
            id=1,
            reservation_id=1,
            slot_table_id=1,
            assigned_seats=4,
        ),
        ReservationTableAssignmentDAO(
            id=2,
            reservation_id=1,
            slot_table_id=2,
            assigned_seats=1,
        ),
        ReservationTableAssignmentDAO(
            id=3,
            reservation_id=1,
            slot_table_id=3,
            assigned_seats=1,
        ),
    ]

    db.add_all([
        alice,
        bob,
        table1,
        table2,
        table3,
        open_slot,
        closed_slot,
        *slot_tables,
        reservation,
        *assignments,
    ])
    db.commit()

    return alice, bob, open_slot, closed_slot


def test_slot_availability_shows_total_and_per_table_free_seats(client, db):
    """Availability reports the remaining capacity of each table."""
    seed_availability_data(db)

    response = client.get("/api/slots/1/availability")

    assert response.status_code == 200
    body = response.json()

    assert body["slot_id"] == 1
    assert body["total_capacity"] == 12
    assert body["reserved_seats"] == 6
    assert body["remaining_seats"] == 6
    assert body["is_available"] is True

    tables = {
        table["table_number"]: table
        for table in body["tables"]
    }
    assert tables["T1"]["free_seats"] == 2
    assert tables["T2"]["free_seats"] == 3
    assert tables["T3"]["free_seats"] == 1


def test_slot_availability_returns_layout_for_party_size(client, db):
    """A party of six can use the fragmented free seats across three tables."""
    seed_availability_data(db)

    response = client.get(
        "/api/slots/1/availability",
        params={"party_size": 6},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["is_available"] is True
    assert body["layout_summary"] == "3 + 2 + 1 seats"
    assert len(body["layout"]) == 3
    assert sum(item["assigned_seats"] for item in body["layout"]) == 6


def test_booking_updates_slot_availability_until_full(client, db, monkeypatch):
    """A successful booking deducts the remaining seats from availability."""
    alice, _, _, _ = seed_availability_data(db)
    # 1. Check availability before booking
    initial_availability = client.get("/api/slots/1/availability")

    assert initial_availability.status_code == 200
    initial_body = initial_availability.json()

    assert initial_body["total_capacity"] == 12
    assert initial_body["reserved_seats"] == 6
    assert initial_body["remaining_seats"] == 6
    assert initial_body["is_available"] is True

    # 2. Check booking was successful
    assert booking.status_code == 201
    booking_data = booking.json()

    assert booking_data["status"] == "CONFIRMED"
    assert booking_data["party_size"] == 6
    assert booking_data["booking_reference"]

    # 3. Check availability after booking
    availability = client.get("/api/slots/1/availability")

    assert availability.status_code == 200
    body = availability.json()

    assert body["total_capacity"] == 12
    assert body["reserved_seats"] == 12
    assert body["remaining_seats"] == 0
    assert body["is_available"] is False


    monkeypatch.setattr(
        "server.controllers.reservation_controller.send_booking_confirmation_email",
        lambda mail: {"status": "SENT"},
    )

    token = generate_token(alice)
    headers = {"Authorization": f"Bearer {token}"}

    booking = client.post(
        "/api/reservations",
        json={
            "slot_id": 1,
            "party_size": 6,
            "user_id": alice.id,
            "contact_name": "Alice Walker",
            "contact_email": "alice@test.com",
            "contact_phone": "+39 340 1112233",
        },
        headers=headers,
    )

    assert booking.status_code == 201

    availability = client.get("/api/slots/1/availability")

    assert availability.status_code == 200
    body = availability.json()
    assert body["reserved_seats"] == 12
    assert body["remaining_seats"] == 0
    assert body["is_available"] is False


def test_closed_slot_is_unavailable_even_when_it_has_free_seats(client, db):
    """A closed slot is unavailable even though its tables have free seats."""
    seed_availability_data(db)

    response = client.get(
        "/api/slots/2/availability",
        params={"party_size": 2},
    )

    assert response.status_code == 200
    body = response.json()

    assert body["status"] == SlotStatus.CLOSED.value
    assert body["remaining_seats"] == 6
    assert body["is_available"] is False
    assert body["layout"] == []


def test_unknown_slot_returns_not_found(client, db):
    """Requesting availability for a slot that does not exist returns 404."""
    seed_availability_data(db)

    response = client.get("/api/slots/999/availability")

    assert response.status_code == 404
