"""DTO schemas package."""
from server.models.DTO.reservation_dto import (
    ReservationCreate,
    ReservationResponse,
    AssignedTableInfo,
    SlotAvailabilityResponse,
    TableLayoutAssignment,
    TableCapacityInfo,
    SpecialRequirementDTO,
)

__all__ = [
    "ReservationCreate",
    "ReservationResponse",
    "AssignedTableInfo",
    "SlotAvailabilityResponse",
    "TableLayoutAssignment",
    "TableCapacityInfo",
    "SpecialRequirementDTO",
]

