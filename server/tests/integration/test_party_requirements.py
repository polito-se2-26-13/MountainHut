"""Integration tests of MH-05, party requirements: a booking has a list of requirements,
each with its own allergy flag and description, as in the example of the story."""
from test_booking import TOKENS, add_hiker, add_slot, book

REQUIREMENTS = [
    {"has_allergy": True, "description": "1 vegan, peanut allergy"},
    {"has_allergy": False, "description": "2 vegetarians"},
]


def test_each_requirement_is_saved_with_its_allergy_flag(client, db):
    anna = add_hiker(db)

    response = book(client, anna, add_slot(db, [6]), 4, special_requirements=REQUIREMENTS)

    assert response.status_code == 201
    read = client.get(f"/api/reservations/reference/{response.json()['booking_reference']}", headers=TOKENS[anna])
    for booking in (response.json(), read.json()):
        assert booking["special_requirements"] == REQUIREMENTS


def test_a_requirement_without_a_description_is_refused(client, db):
    anna = add_hiker(db)

    response = book(client, anna, add_slot(db, [6]), 4, special_requirements=[{"has_allergy": True, "description": "   "}])

    assert response.status_code == 422
