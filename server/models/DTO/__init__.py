"""DTO schemas package."""
from server.models.DTO.reservation_dto import (
    ReservationCreate,
    ReservationResponse,
    AssignedTableInfo,
    SlotAvailabilityResponse,
)

__all__ = [
    "ReservationCreate",
    "ReservationResponse",
    "AssignedTableInfo",
    "SlotAvailabilityResponse",
]
