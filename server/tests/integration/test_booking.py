"""Integration tests of the Book a table story (MH-01): POST /api/reservations,
GET /api/reservations/{reference} and GET /api/slots/{slot_id}/availability."""
from datetime import datetime, timedelta

from server.models.DAO.reservation import ReservationDAO
from server.models.DAO.table import TableDAO
from server.models.DAO.time_slot import SlotTableDAO, TimeSlotDAO
from server.models.DAO.user import UserDAO
from server.service.auth_service import generate_token

# the login token of each hiker of the test, by id
TOKENS = {}


def add_hiker(db, email="anna@example.com"):
    hiker = UserDAO(email=email, password_hash="x", first_name="Anna", last_name="Rossi", role="Hiker")
    db.add(hiker)
    db.commit()
    TOKENS[hiker.id] = {"Authorization": f"Bearer {generate_token(hiker)}"}
    return hiker.id


def add_slot(db, seats, hours_ahead=24, status="OPEN"):
    """A slot starting hours_ahead from now, with one table for each number in seats."""
    start = datetime.now().replace(microsecond=0) + timedelta(hours=hours_ahead)
    slot = TimeSlotDAO(
        date=start.date(),
        start_time=start.time(),
        end_time=(start + timedelta(hours=1)).time(),
        meal_type="Lunch",
        status=status,
    )
    db.add(slot)
    db.flush()
    for number, capacity in enumerate(seats, start=1):
        table = TableDAO(table_number=f"{slot.id}-{number}", capacity=capacity)
        db.add(table)
        db.flush()
        db.add(SlotTableDAO(slot_id=slot.id, table_id=table.id, available_seats=capacity))
    db.commit()
    return slot.id


def book(client, hiker, slot, party_size):
    return client.post("/api/reservations", json={
        "slot_id": slot,
        "party_size": party_size,
        "user_id": hiker,
        "contact_name": "Anna Rossi",
        "contact_email": "anna@example.com",
    }, headers=TOKENS[hiker])


def seats_by_table(response):
    return {t["table_number"]: t["assigned_seats"] for t in response.json()["assigned_tables"]}


def test_party_gets_a_table_and_the_booking_is_saved(client, db):
    hiker = add_hiker(db)
    slot = add_slot(db, [6])

    response = book(client, hiker, slot, 4)

    assert response.status_code == 201
    booking = response.json()
    assert booking["status"] == "CONFIRMED"
    assert booking["booking_reference"]
    assert seats_by_table(response) == {f"{slot}-1": 4}
    saved = db.get(ReservationDAO, booking["id"])
    assert saved.slot_id == slot
    assert saved.party_size == 4


def test_party_takes_the_smallest_table_that_fits(client, db):
    hiker = add_hiker(db)
    slot = add_slot(db, [6, 4, 2])

    response = book(client, hiker, slot, 3)

    assert response.status_code == 201
    assert seats_by_table(response) == {f"{slot}-2": 3}


def test_parties_share_a_table(client, db):
    anna = add_hiker(db)
    marco = add_hiker(db, "marco@example.com")
    slot = add_slot(db, [6])

    first = book(client, anna, slot, 2)
    second = book(client, marco, slot, 3)

    assert first.status_code == 201
    assert second.status_code == 201
    assert seats_by_table(first) == {f"{slot}-1": 2}
    assert seats_by_table(second) == {f"{slot}-1": 3}


def test_party_is_split_only_when_no_table_fits(client, db):
    hiker = add_hiker(db)
    slot = add_slot(db, [4, 4])

    response = book(client, hiker, slot, 6)

    assert response.status_code == 201
    tables = seats_by_table(response)
    assert len(tables) == 2
    assert sum(tables.values()) == 6


def test_split_uses_as_few_tables_as_possible(client, db):
    hiker = add_hiker(db)
    slot = add_slot(db, [2, 2, 5, 3])

    response = book(client, hiker, slot, 8)

    assert response.status_code == 201
    assert seats_by_table(response) == {f"{slot}-3": 5, f"{slot}-4": 3}


def test_split_leaves_the_larger_tables_free_for_the_next_party(client, db):
    anna = add_hiker(db)
    marco = add_hiker(db, "marco@example.com")
    slot = add_slot(db, [8, 6, 4])

    first = book(client, anna, slot, 11)
    second = book(client, marco, slot, 5)

    assert seats_by_table(first) == {f"{slot}-1": 8, f"{slot}-3": 3}
    assert seats_by_table(second) == {f"{slot}-2": 5}


def test_party_larger_than_the_free_seats_is_refused(client, db):
    hiker = add_hiker(db)
    slot = add_slot(db, [4, 2])

    response = book(client, hiker, slot, 7)

    assert response.status_code == 409
    assert db.query(ReservationDAO).count() == 0


def test_slot_without_tables_cannot_be_booked(client, db):
    hiker = add_hiker(db)
    slot = add_slot(db, [])

    response = book(client, hiker, slot, 1)

    assert response.status_code == 409
    assert client.get(f"/api/slots/{slot}/availability").json()["total_capacity"] == 0


def test_booking_closes_two_hours_before_the_slot(client, db):
    hiker = add_hiker(db)
    too_late = add_slot(db, [4], hours_ahead=1)
    in_time = add_slot(db, [4], hours_ahead=3)

    assert book(client, hiker, too_late, 2).status_code == 409
    assert book(client, hiker, in_time, 2).status_code == 201


def test_one_booking_per_hiker_in_a_slot(client, db):
    hiker = add_hiker(db)
    slot = add_slot(db, [6])
    other_slot = add_slot(db, [6], hours_ahead=30)

    assert book(client, hiker, slot, 2).status_code == 201
    assert book(client, hiker, slot, 2).status_code == 409
    assert book(client, hiker, other_slot, 2).status_code == 201
    assert client.get(f"/api/slots/{slot}/availability").json()["reserved_seats"] == 2


def test_closed_slot_cannot_be_booked(client, db):
    hiker = add_hiker(db)
    slot = add_slot(db, [6], status="CLOSED")

    assert book(client, hiker, slot, 2).status_code == 409


def test_availability_counts_the_booked_seats(client, db):
    hiker = add_hiker(db)
    slot = add_slot(db, [6, 4])

    book(client, hiker, slot, 3)
    response = client.get(f"/api/slots/{slot}/availability")

    assert response.status_code == 200
    seats = response.json()
    assert seats["total_capacity"] == 10
    assert seats["reserved_seats"] == 3
    assert seats["remaining_seats"] == 7


def test_unknown_slot(client, db):
    hiker = add_hiker(db)

    assert book(client, hiker, 999, 2).status_code == 404
    assert client.get("/api/slots/999/availability").status_code == 404


def test_party_size_is_required_and_positive(client, db):
    hiker = add_hiker(db)
    slot = add_slot(db, [6])

    missing = client.post("/api/reservations", json={
        "slot_id": slot, "user_id": hiker, "contact_name": "Anna Rossi", "contact_email": "anna@example.com",
    }, headers=TOKENS[hiker])

    assert missing.status_code == 422
    assert book(client, hiker, slot, 0).status_code == 422


def test_booking_needs_the_login_of_a_hiker(client, db):
    slot = add_slot(db, [6])
    body = {"slot_id": slot, "party_size": 2, "contact_name": "Anna Rossi", "contact_email": "anna@example.com"}
    employee = UserDAO(email="employee@example.com", password_hash="x", first_name="E", last_name="E", role="Employee")
    db.add(employee)
    db.commit()

    assert client.post("/api/reservations", json=body).status_code == 401
    response = client.post("/api/reservations", json=body, headers={"Authorization": f"Bearer {generate_token(employee)}"})

    assert response.status_code == 403
    assert db.query(ReservationDAO).count() == 0


def test_booking_belongs_to_the_hiker_of_the_token(client, db):
    anna = add_hiker(db)
    other = add_hiker(db, email="other@example.com")
    slot = add_slot(db, [6])

    response = client.post("/api/reservations", json={
        "slot_id": slot, "party_size": 2, "user_id": other, "contact_name": "Anna Rossi", "contact_email": "anna@example.com",
    }, headers=TOKENS[anna])

    assert response.status_code == 201
    assert response.json()["user_id"] == anna


def test_booking_can_be_read_by_its_reference(client, db):
    hiker = add_hiker(db)
    # a table outside the slot, so that a table id and a slot table id are different numbers
    db.add(TableDAO(table_number="spare", capacity=2))
    db.commit()
    slot = add_slot(db, [6])
    booking = book(client, hiker, slot, 2).json()

    response = client.get(f"/api/reservations/{booking['booking_reference']}", headers=TOKENS[hiker])

    assert response.status_code == 200
    assert response.json()["id"] == booking["id"]
    assert response.json()["assigned_tables"][0]["table_number"] == f"{slot}-1"
    assert client.get("/api/reservations/NOPE", headers=TOKENS[hiker]).status_code == 404


def test_bookings_are_read_only_with_the_login(client, db):
    anna = add_hiker(db)
    booking = book(client, anna, add_slot(db, [6]), 2).json()

    assert client.get(f"/api/reservations/user/{anna}").status_code == 401
    assert client.get(f"/api/reservations/{booking['booking_reference']}").status_code == 401


def test_a_hiker_reads_only_their_own_bookings(client, db):
    anna = add_hiker(db)
    other = add_hiker(db, email="other@example.com")
    booking = book(client, anna, add_slot(db, [6]), 2).json()
    employee = UserDAO(email="employee@example.com", password_hash="x", first_name="E", last_name="E", role="Employee")
    db.add(employee)
    db.commit()

    assert client.get(f"/api/reservations/user/{anna}", headers=TOKENS[other]).status_code == 403
    assert client.get(f"/api/reservations/{booking['booking_reference']}", headers=TOKENS[other]).status_code == 403
    mine = client.get(f"/api/reservations/user/{anna}", headers=TOKENS[anna])
    assert mine.status_code == 200
    assert [b["id"] for b in mine.json()] == [booking["id"]]
    # the hut staff can look up any booking by its reference
    staff = client.get(f"/api/reservations/{booking['booking_reference']}", headers={"Authorization": f"Bearer {generate_token(employee)}"})
    assert staff.status_code == 200


def test_a_hiker_without_bookings_gets_an_empty_list(client, db):
    anna = add_hiker(db)

    response = client.get(f"/api/reservations/user/{anna}", headers=TOKENS[anna])

    assert response.status_code == 200
    assert response.json() == []
