"""Application-wide constants and enumerations."""
from enum import Enum


class UserRole(str, Enum):
    """User roles according to context.md and auth flow."""
    HIKER = "Hiker"
    EMPLOYEE = "Employee"
    WARDEN = "Warden"
    MANAGER = "Manager"  # Alias/equivalent to Warden in some UI flows


class SlotStatus(str, Enum):
    """Status for meal time slots."""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class ReservationStatus(str, Enum):
    """Status for table reservations."""
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"

