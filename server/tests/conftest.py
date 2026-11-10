import pytest


@pytest.fixture(autouse=True)
def no_real_mail(monkeypatch):
    """With a server/.env every booking of the tests would really send a mail."""
    monkeypatch.setattr(
        "server.controllers.reservation_controller.send_booking_confirmation_email",
        lambda mail: {"status": "SENT"},
    )
