
import pytest
from types import SimpleNamespace

from server.service.email_service import (
    format_booking_email_text,
    format_booking_email_html,
    send_booking_confirmation_email,
)


@pytest.fixture
def reservation():
    """Create a sample reservation for email tests."""

    confirmation_data = {
        "bookingReference": "MH-20261104-ABC123",
        "hikerName": "Alice Walker",
        "hikerEmail": "hiker@test.com",
        "date": "2030-11-15",
        "timeSlot": "12:00 - 13:00",
        "partySize": 4,
        "specialRequirements": "Vegetarian meal",
        "assignedTables": [
            {
                "tableNumber": "T1",
                "tableLocation": "Indoor",
                "seatsAssigned": 4,
            }
        ],
    }

    return SimpleNamespace(
        booking_reference="MH-20261104-ABC123",
        contact_email="hiker@test.com",
        to_confirmation_dict=lambda: confirmation_data,
    )


def test_format_booking_email_text(reservation):
    """Test that the plain text email contains booking details."""

    email = format_booking_email_text(reservation)

    assert "Alice Walker" in email
    assert "MH-20261104-ABC123" in email
    assert "2030-11-15" in email
    assert "12:00 - 13:00" in email
    assert "4 person(s)" in email
    assert "Vegetarian meal" in email
    assert "Table T1" in email
    assert "Indoor" in email


def test_format_booking_email_html(reservation):
    """Test that the HTML email contains booking details."""

    email = format_booking_email_html(reservation)

    assert "<html" in email
    assert "Alice Walker" in email
    assert "MH-20261104-ABC123" in email
    assert "2030-11-15" in email
    assert "12:00 - 13:00" in email
    assert "4 person(s)" in email
    assert "Vegetarian meal" in email
    assert "Table T1" in email
    assert "Indoor" in email


def test_send_booking_confirmation_email_generates_payload(reservation):
    """Test the confirmation email payload."""

    result = send_booking_confirmation_email(reservation)

    assert result["status"] == "SENT"
    assert result["to"] == "hiker@test.com"
    assert result["booking_reference"] == "MH-20261104-ABC123"

    assert result["subject"] == (
        "Mountain Hut Booking Confirmation [MH-20261104-ABC123]"
    )

    assert "Alice Walker" in result["text_content"]
    assert "MH-20261104-ABC123" in result["html_content"]


def test_email_with_no_special_requirements(reservation):
    """Test email formatting when no special requirements are provided."""

    reservation.to_confirmation_dict = lambda: {
        "bookingReference": "MH-TEST-002",
        "hikerName": "Bob Smith",
        "date": "2030-11-15",
        "timeSlot": "19:00 - 20:30",
        "partySize": 2,
        "specialRequirements": None,
        "assignedTables": [],
    }

    text_email = format_booking_email_text(reservation)
    html_email = format_booking_email_html(reservation)

    assert "None specified" in text_email
    assert "Assigned upon arrival" in text_email
    assert "Assigned upon arrival" in html_email
def test_email_with_missing_booking_information(reservation):
    reservation.to_confirmation_dict = lambda: {
        "bookingReference": None,
        "hikerName": None,
        "date": None,
        "timeSlot": None,
        "partySize": None,
        "specialRequirements": None,
        "assignedTables": [],
    }

    text = format_booking_email_text(reservation)
    html = format_booking_email_html(reservation)

    assert "Valued Guest" in text
    assert "Valued Guest" in html
    assert "N/A" in text
    assert "None specified" in text
    assert "Assigned upon arrival" in text

def test_email_payload_contains_matching_recipient_and_bodies(reservation):
    """The generated payload uses the reservation's recipient and formatted bodies."""
    result = send_booking_confirmation_email(reservation)

    assert result["to"] == reservation.contact_email
    assert result["booking_reference"] == reservation.booking_reference
    assert result["text_content"] == format_booking_email_text(reservation)
    assert result["html_content"] == format_booking_email_html(reservation)
