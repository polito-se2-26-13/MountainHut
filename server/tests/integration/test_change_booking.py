"""Integration tests of MH-06, change a booking: PUT /api/reservations/reference/{reference}/change.
Any change is treated as a new booking (PO issues #38 and #48) and is notified by email (#41)."""
from server.service.email_service import format_booking_email_html, format_booking_email_text
from test_booking import TOKENS, add_hiker, add_slot, book, seats_by_table


def change(client, hiker, booking, **changes):
    # the whole booking with the changes, as the change window of the history page sends it (PR #42)
    body = {key: booking[key] for key in ("slot_id", "party_size", "special_requirements")}
    return client.put(f"/api/reservations/reference/{booking['booking_reference']}/change",
                      json={**body, **changes}, headers=TOKENS[hiker])


def test_a_change_is_confirmed_by_email_with_the_new_details(client, db, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "server.controllers.reservation_controller.send_booking_confirmation_email",
        lambda mail: sent.append(mail) or {"status": "SENT"},
    )
    anna = add_hiker(db)
    booking = book(client, anna, add_slot(db, [6], hours_ahead=72), 2).json()

    response = change(client, anna, booking, party_size=4,
                      special_requirements=[{"has_allergy": True, "description": "1 gluten allergy"}])

    assert response.status_code == 200
    mail = sent[-1]
    assert len(sent) == 2 and mail.contact_email == "anna@example.com"
    text, html = format_booking_email_text(mail), format_booking_email_html(mail)
    assert "4 person(s)" in text and "ALLERGY: 1 gluten allergy" in text and html.count("Allergy:") == 1


def test_a_party_grows_on_its_own_table_when_the_seats_are_enough(client, db):
    # its own seats are given back first: 3 on the only table of 4, then 4
    anna = add_hiker(db)
    slot = add_slot(db, [4], hours_ahead=72)
    booking = book(client, anna, slot, 3).json()

    response = change(client, anna, booking, party_size=4)

    assert response.status_code == 200
    assert seats_by_table(response) == {f"{slot}-1": 4}


def test_a_party_that_no_longer_fits_keeps_its_booking(client, db):
    anna = add_hiker(db)
    slot = add_slot(db, [4], hours_ahead=72)
    booking = book(client, anna, slot, 3).json()

    response = change(client, anna, booking, party_size=5)

    assert response.status_code == 409
    read = client.get(f"/api/reservations/reference/{booking['booking_reference']}", headers=TOKENS[anna])
    assert read.json()["party_size"] == 3
    assert seats_by_table(read) == {f"{slot}-1": 3}


def test_a_booking_moves_only_to_a_slot_at_least_48_hours_away(client, db):
    # PO issue #43: the 48 hours hold for the old slot and for the new one
    anna = add_hiker(db)
    booking = book(client, anna, add_slot(db, [6], hours_ahead=72), 2).json()

    for hours in (1, 24):
        assert change(client, anna, booking, slot_id=add_slot(db, [6], hours_ahead=hours)).status_code == 409
    in_three_days = add_slot(db, [6], hours_ahead=80)
    assert change(client, anna, booking, slot_id=in_three_days).json()["slot_id"] == in_three_days


def test_the_list_sent_replaces_the_requirements(client, db):
    anna = add_hiker(db)
    gluten = [{"has_allergy": True, "description": "1 gluten allergy"}]
    booking = book(client, anna, add_slot(db, [6], hours_ahead=72), 2, special_requirements=gluten).json()

    assert change(client, anna, booking, party_size=3).json()["special_requirements"] == gluten
    assert change(client, anna, booking, special_requirements=[]).json()["special_requirements"] == []


def test_a_hiker_changes_only_their_own_bookings(client, db):
    anna = add_hiker(db)
    other = add_hiker(db, email="other@example.com")
    booking = book(client, anna, add_slot(db, [6], hours_ahead=72), 2).json()

    assert change(client, other, booking, party_size=3).status_code == 403

def test_a_change_without_the_requirements_is_refused_and_keeps_them(client, db):
    # the window always sends the list: a missing one must not be read as "remove the allergies"
    anna = add_hiker(db)
    gluten = [{"has_allergy": True, "description": "1 gluten allergy"}]
    booking = book(client, anna, add_slot(db, [6], hours_ahead=72), 2, special_requirements=gluten).json()

    response = client.put(f"/api/reservations/reference/{booking['booking_reference']}/change",
                          json={"slot_id": booking["slot_id"], "party_size": 3}, headers=TOKENS[anna])

    assert response.status_code == 422
    read = client.get(f"/api/reservations/reference/{booking['booking_reference']}", headers=TOKENS[anna])
    assert read.json()["special_requirements"] == gluten

def test_a_party_changes_in_a_slot_shared_with_other_bookings(client, db):
    # the other bookings of the slot are counted too, as in the sample data
    anna = add_hiker(db)
    other = add_hiker(db, email="other@example.com")
    slot = add_slot(db, [4, 6], hours_ahead=72)
    book(client, other, slot, 4)
    booking = book(client, anna, slot, 2).json()

    response = change(client, anna, booking, party_size=5)

    assert response.status_code == 200
    assert sum(seats_by_table(response).values()) == 5

def test_a_booking_moved_to_a_full_slot_is_told_there_are_not_enough_seats(client, db):
    anna = add_hiker(db)
    other = add_hiker(db, email="other@example.com")
    full = add_slot(db, [4], hours_ahead=80)
    book(client, other, full, 4)
    booking = book(client, anna, add_slot(db, [6], hours_ahead=72), 2).json()

    response = change(client, anna, booking, slot_id=full)

    assert response.status_code == 409
    assert "Not enough seats" in response.json()["message"]
