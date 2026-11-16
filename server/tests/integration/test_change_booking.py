"""Integration tests of MH-06, change a booking: PATCH /api/reservations/reference/{reference}.
Any change is treated as a new booking (PO issues #38 and #48) and is notified by email (#41)."""
from test_booking import TOKENS, add_hiker, add_slot, book


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
        # PO issue #24: the mail has no table numbers
        assert f"{slot}-1" not in body and "Assigned" not in body
