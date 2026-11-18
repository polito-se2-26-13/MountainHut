from datetime import date, time, timedelta

from server.models.DAO.reservation import ReservationDAO
from server.models.DAO.table import TableDAO
from server.models.DAO.time_slot import SlotTableDAO, TimeSlotDAO
from server.models.DAO.user import UserDAO
from server.models.enum.slot_status import SlotStatus
from server.models.enum.user_type import UserType
from server.service.auth_service import generate_token


def seed_party_requirements_data(db):
    """Create a hiker and an open slot with enough capacity."""
    user = UserDAO(
        email="alice.party.requirements@test.com",
        password_hash="dummy",
        first_name="Alice",
        last_name="Walker",
        phone="+39 340 1112233",
        role=UserType.HIKER.value,
    )
    table = TableDAO(
        table_number="T1",
        capacity=6,
        location="Main Hall",
    )
    slot = TimeSlotDAO(
        date=date.today() + timedelta(days=7),
        start_time=time(12, 30),
        end_time=time(13, 30),
        meal_type="Lunch",
        status=SlotStatus.OPEN.value,
    )

    db.add_all([user, table, slot])
    db.flush()

    slot_table = SlotTableDAO(
        slot_id=slot.id,
        table_id=table.id,
        available_seats=6,
        is_available=True,
    )
    db.add(slot_table)
    db.commit()
    db.refresh(user)
    db.refresh(slot)
    return user, slot


def test_legacy_party_requirements_are_saved_and_returned(
    client, db, monkeypatch
):
    """The current free-text requirements field survives create/read."""
    user, slot = seed_party_requirements_data(db)
    requirements = "1 vegan, peanut allergy; 1 vegetarian"

    # Avoid sending a real email during the test.
    monkeypatch.setattr(
        "server.controllers.reservation_controller.send_booking_confirmation_email",
        lambda mail: {"status": "SENT"},
    )

    headers = {"Authorization": f"Bearer {generate_token(user)}"}

    response = client.post(
        "/api/reservations",
        json={
            "slot_id": slot.id,
            "party_size": 2,
            "contact_name": "Alice Walker",
            "contact_email": user.email,
            "contact_phone": user.phone,
            "special_requirements": requirements,
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    response_data = response.json()
    booking_reference = response_data["booking_reference"]
    assert booking_reference

    saved_reservation = (
        db.query(ReservationDAO)
        .filter_by(booking_reference=booking_reference)
        .first()
    )
    assert saved_reservation is not None
    assert saved_reservation.special_requirements == requirements

    retrieved_response = client.get(
        f"/api/reservations/reference/{booking_reference}",
        headers=headers,
    )

    assert retrieved_response.status_code == 200, retrieved_response.text
    retrieved_data = retrieved_response.json()
    assert retrieved_data["booking_reference"] == booking_reference
    assert retrieved_data["special_requirements"] == requirements

    db.refresh(saved_reservation)
    assert saved_reservation.special_requirements == requirements
