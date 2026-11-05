
import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock
import server.service.email_service as email_service
from server.service.email_service import (
    format_booking_email_text,
    format_booking_email_html,
    send_booking_confirmation_email,
)


@pytest.fixture
def reservation():
    """Create a sample reservation for email tests."""

    return SimpleNamespace(
        booking_reference="MH-20261104-ABC123",
        contact_email="hiker@test.com",
        date_str="2030-11-15",
        time_slot="12:00 - 13:00",
        contact_name="Alice Walker",
        party_size=4,
        special_reqs="Vegetarian meal",
        tables=[
            {
                "tableNumber": "T1",
                "tableLocation": "Indoor",
                "assignedSeats": 4,
            }
        ],
    )

def test_format_booking_email_text(reservation):
    """Test that the plain text email contains booking details."""

    email = format_booking_email_text(reservation)

    assert "Valued Guest" in email
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
    assert "Valued Guest" in email
    assert "MH-20261104-ABC123" in email
    assert "2030-11-15" in email
    assert "12:00 - 13:00" in email
    assert "4 person(s)" in email
    assert "Vegetarian meal" in email
    assert "Table T1" in email
    assert "Indoor" in email


def test_send_booking_confirmation_email_generates_payload(
    reservation, mock_smtp
):
    result = send_booking_confirmation_email(reservation)

    assert result["status"] == "SENT"
    assert result["to"] == "hiker@test.com"
    assert result["booking_reference"] == "MH-20261104-ABC123"

    assert result["subject"] == (
        "Mountain Hut Booking Confirmation [MH-20261104-ABC123]"
    )

    assert "Valued Guest" in result["text_content"]
    assert "MH-20261104-ABC123" in result["html_content"]

    mock_smtp.send_message.assert_called_once()


def test_email_with_no_special_requirements(reservation):
    reservation.special_reqs = None
    reservation.tables = []

    text_email = format_booking_email_text(reservation)
    html_email = format_booking_email_html(reservation)

    assert "None" in text_email
    assert "Assigned upon arrival" in text_email
    assert "Assigned upon arrival" in html_email


def test_email_with_missing_booking_information(reservation):
    reservation.booking_reference = None
    reservation.date_str = None
    reservation.time_slot = None
    reservation.party_size = None
    reservation.special_reqs = None
    reservation.tables = []

    text = format_booking_email_text(reservation)
    html = format_booking_email_html(reservation)

    assert "Valued Guest" in text
    assert "Valued Guest" in html
    assert "None" in text
    assert "Assigned upon arrival" in text

def test_email_payload_contains_matching_recipient_and_bodies(
    reservation, mock_smtp
):
    result = send_booking_confirmation_email(reservation)

    assert result["to"] == reservation.contact_email
    assert result["booking_reference"] == reservation.booking_reference
    assert result["text_content"] == format_booking_email_text(reservation)
    assert result["html_content"] == format_booking_email_html(reservation)

    mock_smtp.send_message.assert_called_once()

@pytest.fixture
def mock_smtp(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "localhost")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_EMAIL", "test@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "test-password")

    mock_server = MagicMock()
    mock_context = MagicMock()
    mock_context.__enter__.return_value = mock_server

    smtp_mock = MagicMock(return_value=mock_context)
    monkeypatch.setattr(
        email_service.smtplib, "SMTP", smtp_mock
    )
    return mock_server