"""Unit tests for MountainHut Availability Rules (MH-04)."""

from datetime import date, time

import pytest

from server.models.DAO.reservation import (
    ReservationDAO,
    ReservationTableAssignmentDAO,
)
from server.models.DAO.table import TableDAO
from server.models.DAO.time_slot import SlotTableDAO, TimeSlotDAO
from server.models.enum.reservation_status import ReservationStatus
from server.models.enum.slot_status import SlotStatus
from server.repositories.reservation_repository import ReservationRepository


def build_slot_table(
    slot_table_id: int,
    table_number: str,
    capacity: int,
    confirmed_seats: int = 0,
    is_available: bool = True,
    location: str = "Indoor",
) -> SlotTableDAO:
    """Build an in-memory slot-table relationship with reservation assignments."""
    table = TableDAO(
        id=slot_table_id,
        table_number=table_number,
        capacity=capacity,
        location=location,
    )

    assignments = []
    if confirmed_seats:
        confirmed_reservation = ReservationDAO(
            status=ReservationStatus.CONFIRMED.value
        )
        assignments.append(
            ReservationTableAssignmentDAO(
                assigned_seats=confirmed_seats,
                reservation=confirmed_reservation,
            )
        )

    return SlotTableDAO(
        id=slot_table_id,
        slot_id=1,
        table_id=slot_table_id,
        available_seats=capacity,
        is_available=is_available,
        table=table,
        assignments=assignments,
    )


def build_slot(
    slot_id: int = 1,
    status: str = SlotStatus.OPEN.value,
    slot_tables: list[SlotTableDAO] | None = None,
) -> TimeSlotDAO:
    """Build an in-memory time slot."""
    slot = TimeSlotDAO(
        id=slot_id,
        date=date(2030, 11, 15),
        start_time=time(12, 0),
        end_time=time(13, 0),
        meal_type="Lunch",
        status=status,
    )
    slot.slot_tables = slot_tables or []
    return slot


class InMemoryReservationRepository(ReservationRepository):
    """Use real repository availability logic with in-memory slot objects."""

    def __init__(self, slots: dict[int, TimeSlotDAO] | None = None):
        self.slots = slots or {}

    async def get_time_slot(self, slot_id: int):
        return self.slots.get(slot_id)


@pytest.mark.asyncio
async def test_availability_lists_the_tables_in_order_and_has_no_layout_without_party_size():
    slot = build_slot(
        slot_tables=[
            build_slot_table(1, "T2", capacity=4, confirmed_seats=1),
            build_slot_table(2, "T1", capacity=6, confirmed_seats=2),
        ]
    )
    repository = InMemoryReservationRepository({1: slot})

    result = await repository.get_slot_availability(slot_id=1)

    assert result["layout"] is None
    assert result["layout_summary"] is None
    assert [table["table_number"] for table in result["tables"]] == ["T1", "T2"]


@pytest.mark.asyncio
async def test_fully_booked_slot_is_unavailable():
    slot = build_slot(
        slot_tables=[
            build_slot_table(1, "T1", capacity=4, confirmed_seats=4),
        ]
    )
    repository = InMemoryReservationRepository({1: slot})

    result = await repository.get_slot_availability(slot_id=1)

    assert result["total_capacity"] == 4
    assert result["reserved_seats"] == 4
    assert result["remaining_seats"] == 0
    assert result["is_available"] is False


@pytest.mark.asyncio
async def test_single_table_best_fit_returns_expected_layout():
    slot = build_slot(
        slot_tables=[
            build_slot_table(1, "T1", capacity=6),
            build_slot_table(2, "T2", capacity=4),
        ]
    )
    repository = InMemoryReservationRepository({1: slot})

    result = await repository.get_slot_availability(slot_id=1, party_size=3)

    assert result["is_available"] is True
    assert result["layout_summary"] == "3 seat(s) at Table T2"
    assert result["layout"] == [
        {
            "table_number": "T2",
            "assigned_seats": 3,
            "location": "Indoor",
        }
    ]


@pytest.mark.asyncio
async def test_fragmented_free_seats_can_accommodate_party():
    slot = build_slot(
        slot_tables=[
            build_slot_table(1, "T10", capacity=6, confirmed_seats=4),
            build_slot_table(2, "T11", capacity=4, confirmed_seats=1),
            build_slot_table(3, "T12", capacity=2, confirmed_seats=1),
        ]
    )
    repository = InMemoryReservationRepository({1: slot})

    result = await repository.get_slot_availability(slot_id=1, party_size=6)

    assert result["remaining_seats"] == 6
    assert result["is_available"] is True
    assert result["layout_summary"] == "3 + 2 + 1 seats"
    assert sum(item["assigned_seats"] for item in result["layout"]) == 6


@pytest.mark.asyncio
async def test_unavailable_tables_are_excluded_from_capacity():
    slot = build_slot(
        slot_tables=[
            build_slot_table(1, "T1", capacity=6, is_available=True),
            build_slot_table(2, "T2", capacity=4, is_available=False),
        ]
    )
    repository = InMemoryReservationRepository({1: slot})

    result = await repository.get_slot_availability(slot_id=1)

    assert result["total_capacity"] == 6
    assert result["remaining_seats"] == 6
    assert [table["table_number"] for table in result["tables"]] == ["T1"]


@pytest.mark.asyncio
async def test_closed_slot_gives_no_layout_even_with_free_seats():
    slot = build_slot(
        status=SlotStatus.CLOSED.value,
        slot_tables=[build_slot_table(1, "T1", capacity=6)],
    )
    repository = InMemoryReservationRepository({1: slot})

    result = await repository.get_slot_availability(slot_id=1, party_size=2)

    assert result["is_available"] is False
    assert result["layout"] == []
