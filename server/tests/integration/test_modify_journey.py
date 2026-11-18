
"""Integration tests for Modify Journey / Reservation Update."""

import pytest


@pytest.mark.integration
def test_modify_journey_lifecycle(client):
    """Create, retrieve, update, and verify a reservation through the API."""

    # 1. Create a reservation
    create_payload = {
        "slot_id": 1,
        "party_size": 2,
        "contact_name": "Integration Test Hiker",
        "contact_email": "integration@test.com",
        "special_requirements": "Initial reservation",
    }

    create_response = client.post(
        "/api/reservations",
        json=create_payload,
    )

    assert create_response.status_code == 201, create_response.text

    created_reservation = create_response.json()
    reference = created_reservation["reference"]

    assert reference is not None

    # 2. Retrieve the reservation before modification
    get_response = client.get(
        f"/api/reservations/reference/{reference}"
    )

    assert get_response.status_code == 200

    original_reservation = get_response.json()
    assert original_reservation["reference"] == reference
    assert original_reservation["party_size"] == 2

    # 3. Modify the reservation
    update_payload = {
        "party_size": 3,
        "special_requirements": "Updated reservation",
    }

    update_response = client.put(
        f"/api/reservations/reference/{reference}/change",
        json=update_payload,
    )

    assert update_response.status_code == 200, update_response.text

    updated_reservation = update_response.json()

    # 4. Verify the response after modification
    assert updated_reservation["reference"] == reference
    assert updated_reservation["party_size"] == 3
    assert updated_reservation["special_requirements"] == "Updated reservation"

    # 5. Retrieve again to verify persistence
    final_response = client.get(
        f"/api/reservations/reference/{reference}"
    )

    assert final_response.status_code == 200

    final_reservation = final_response.json()

    assert final_reservation["reference"] == reference
    assert final_reservation["party_size"] == 3
    assert final_reservation["special_requirements"] == "Updated reservation"