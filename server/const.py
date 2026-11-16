"""Compatibility exports for enums used by the test suite."""

from server.models.enum.reservation_status import ReservationStatus
from server.models.enum.slot_status import SlotStatus
from server.models.enum.user_type import UserType

# ``UserRole`` is the historical name still used by the unit tests.
UserRole = UserType

__all__ = ["SlotStatus", "ReservationStatus", "UserRole"]
