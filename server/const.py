"""Compatibility exports for status enums used by the test suite."""

from server.models.enum.reservation_status import ReservationStatus
from server.models.enum.slot_status import SlotStatus

__all__ = ["SlotStatus", "ReservationStatus"]
