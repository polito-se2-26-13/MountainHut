"""Integration tests for Modify Journey (MH-06)."""

from test_booking import TOKENS, add_hiker, add_slot, book


def test_modify_journey_lifecycle(client, db, monkeypatch):
    """Create, retrieve, modify and verify a reservation through the API."""

    monkeypatch.setattr(
        "server.controllers.reservation_controller.send_booking_confirmation_email",
        lambda mail: {"status": "SENT"},
    )

    # 1. Create a hiker, the original slot and the new slot.
    hiker = add_hiker(db)
    original_slot = add_slot(db, [6], hours_ahead=72)
    new_slot = add_slot(db, [6], hours_ahead=96)

    headers = TOKENS[hiker]

    # 2. Create the original reservation.
    create_response = book(client, hiker, original_slot, 2)

    assert create_response.status_code == 201, create_response.text

    original_booking = create_response.json()
    reference = original_booking["booking_reference"]

    assert reference
    assert original_booking["slot_id"] == original_slot
    assert original_booking["party_size"] == 2

    # 3. Retrieve the original reservation.
    get_response = client.get(
        f"/api/reservations/reference/{reference}",
        headers=headers,
    )

    assert get_response.status_code == 200, get_response.text

    retrieved_booking = get_response.json()

    assert retrieved_booking["booking_reference"] == reference
    assert retrieved_booking["party_size"] == 2
    assert retrieved_booking["slot_id"] == original_slot

    # 4. Modify the reservation.
    updated_requirements = [
        {
            "has_allergy": True,
            "description": "Peanut allergy",
        },
        {
            "has_allergy": False,
            "description": "Vegetarian meals",
        },
    ]

    update_payload = {
        "slot_id": new_slot,
        "party_size": 3,
        "special_requirements": updated_requirements,
    }

    update_response = client.put(
        f"/api/reservations/reference/{reference}/change",
        json=update_payload,
        headers=headers,
    )

    assert update_response.status_code == 200, update_response.text

    updated_booking = update_response.json()

    # 5. Verify the updated reservation.
    assert updated_booking["booking_reference"] == reference
    assert updated_booking["slot_id"] == new_slot
    assert updated_booking["party_size"] == 3
    assert updated_booking["special_requirements"] == updated_requirements

    # 6. Retrieve the reservation again to verify persistence.
    final_response = client.get(
        f"/api/reservations/reference/{reference}",
        headers=headers,
    )

    assert final_response.status_code == 200, final_response.text

    final_booking = final_response.json()

    assert final_booking["booking_reference"] == reference
    assert final_booking["slot_id"] == new_slot
    assert final_booking["party_size"] == 3
    assert final_booking["special_requirements"] == updated_requirements