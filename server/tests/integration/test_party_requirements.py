"""Integration tests of MH-05, party requirements: a booking has a list of requirements,
each with its own allergy flag and description, as in the example of the story."""
from server.service.email_service import format_booking_email_html, format_booking_email_text
from test_booking import TOKENS, add_hiker, add_slot

REQUIREMENTS = [
    {"has_allergy": True, "description": "1 vegan, peanut allergy"},
    {"has_allergy": False, "description": "2 vegetarians"},
]


def book_with(client, hiker, slot, requirements):
    return client.post("/api/reservations", json={
        "slot_id": slot,
        "party_size": 4,
        "user_id": hiker,
        "contact_name": "Anna Rossi",
        "contact_email": "anna@example.com",
        "special_requirements": requirements,
    }, headers=TOKENS[hiker])


def test_each_requirement_is_saved_with_its_allergy_flag(client, db):
    anna = add_hiker(db)

    response = book_with(client, anna, add_slot(db, [6]), REQUIREMENTS)

    assert response.status_code == 201
    read = client.get(f"/api/reservations/reference/{response.json()['booking_reference']}", headers=TOKENS[anna])
    for booking in (response.json(), read.json()):
        assert [(r["has_allergy"], r["description"]) for r in booking["requirements"]] == [
            (True, "1 vegan, peanut allergy"),
            (False, "2 vegetarians"),
        ]
        assert booking["has_allergies"] is True


def test_the_confirmation_lists_the_requirements_and_flags_only_the_allergy(client, db, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "server.controllers.reservation_controller.send_booking_confirmation_email",
        lambda mail: sent.append(mail) or {"status": "SENT"},
    )
    anna = add_hiker(db)

    book_with(client, anna, add_slot(db, [6]), REQUIREMENTS)

    text, html = format_booking_email_text(sent[0]), format_booking_email_html(sent[0])
    for body in (text, html):
        assert "1 vegan, peanut allergy" in body
        assert "2 vegetarians" in body
    assert html.count("ALLERGY WARNING") == 1
