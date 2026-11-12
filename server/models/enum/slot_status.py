from enum import Enum
"""Status for meal time slots."""
class SlotStatus(str, Enum):

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"