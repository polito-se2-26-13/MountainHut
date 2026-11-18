"""Sending of the confirmation email, with a fake mail server.

The text and HTML of the mail are tested in test_booking_service.py
(test_confirmation_email_follows_the_product_owner and
test_confirmation_email_without_requirements_says_so). Those tests replace the
sending, so this file checks the sending itself.
"""
import pytest
from unittest.mock import MagicMock
import server.service.email_service as email_service
from server.models.DTO.reservation_dto import ReservationMailDTO
from server.service.email_service import send_booking_confirmation_email


@pytest.fixture
def reservation():
    """Create a sample reservation for email tests."""

    return ReservationMailDTO(
        booking_reference="MH-20261104-ABC123",
        contact_email="hiker@test.com",
        date_str="2030-11-15",
        time_slot="12:00 - 13:00",
        hiker_name="Alice Walker",
        party_size=4,
        special_reqs=[{"description": "Vegetarian meal"}],
    )


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

    assert "Alice Walker" in result["text_content"]
    assert "MH-20261104-ABC123" in result["html_content"]

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
