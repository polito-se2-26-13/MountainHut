"""Integration tests of MH-06, change a booking: PATCH /api/reservations/reference/{reference}.
Any change is treated as a new booking (PO issues #38 and #48) and is notified by email (#41)."""
from test_booking import TOKENS, add_hiker, add_slot, book, seats_by_table


def change(client, hiker, booking, **changes):
    return client.patch(f"/api/reservations/reference/{booking['booking_reference']}", json=changes, headers=TOKENS[hiker])


def test_a_change_is_mailed_with_the_new_details_and_without_tables(client, db, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "server.service.email_service.sender_email",
        lambda subject, to, text, html, ref: sent.append((subject, to, text, html)) or {"status": "SENT"},
    )
    anna = add_hiker(db)
    slot = add_slot(db, [6], hours_ahead=72)
    booking = book(client, anna, slot, 2).json()

    response = change(client, anna, booking, party_size=4,
                      special_requirements=[{"has_allergy": True, "description": "1 gluten allergy"}])

    assert response.status_code == 200
    subject, to, text, html = sent[-1]
    assert "Changed" in subject and booking["booking_reference"] in subject
    assert to == "anna@example.com"
    assert "4 person(s)" in text and "changed from" in text and "2 person(s)" in text
    assert html.count("ALLERGY WARNING") == 1
    for body in (text, html):
        # PO issue #24: the mail has no tables ("Assigned Tables", "Table 1-1: 4 seat(s)")
        assert "Assigned" not in body and "seat(s)" not in body


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


def test_a_booking_moves_only_to_a_slot_that_a_new_booking_could_take(client, db):
    # booking closes 2 hours before the slot (MH-01), also when a booking is moved there
    anna = add_hiker(db)
    booking = book(client, anna, add_slot(db, [6], hours_ahead=72), 2).json()
    in_one_hour = add_slot(db, [6], hours_ahead=1)
    in_three_days = add_slot(db, [6], hours_ahead=80)

    assert change(client, anna, booking, slot_id=in_one_hour).status_code == 409
    assert change(client, anna, booking, slot_id=in_three_days).json()["slot_id"] == in_three_days
