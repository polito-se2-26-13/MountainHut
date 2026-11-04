"""An unexpected error must not send its text to the client: for a database error it holds SQL and personal data."""
from server.service.error_service import create_app_error


def test_unknown_error_does_not_show_its_text():
    error = create_app_error(Exception("INSERT INTO reservations ... anna@example.com"))

    assert error.code == 500
    assert error.message == "Internal Server Error"
