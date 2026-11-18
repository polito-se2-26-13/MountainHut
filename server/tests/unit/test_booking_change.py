"""Unit tests for MountainHut Change Booking Rules (MH-06)."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from server.models.DAO.reservation import (
    ReservationDAO,
    ReservationTableAssignmentDAO,
)
from server.models.DAO.table import TableDAO
from server.models.DAO.time_slot import SlotTableDAO, TimeSlotDAO
from server.models.enum.reservation_status import ReservationStatus
from server.models.enum.slot_status import SlotStatus
from server.models.error.conflict_error import ConflictError
from server.service.booking_service import (
    assign_tables_for_party,
    validate_two_hour_rule,
)


def build_slot(
    slot_id: int = 1,
    days_ahead: int = 7,
    start_time: time = time(12, 0),
    status: str = SlotStatus.OPEN.value,
    tables: list[tuple[int, str, int, int, bool]] | None = None,
) -> TimeSlotDAO:
    """Build a transient slot.

    Each table tuple is:
    (slot_table_id, table_number, capacity, seats_occupied_by_others,
    is_available).

    For reallocation tests, the occupied-seat values represent the slot state
    AFTER the old booking's assignments have been released.
    """
    slot_date = datetime.now(ZoneInfo("Europe/Rome")).date() + timedelta(
        days=days_ahead
    )
    slot = TimeSlotDAO(
        id=slot_id,
        date=slot_date,
        start_time=start_time,
        end_time=time((start_time.hour + 1) % 24, start_time.minute),
        meal_type="Lunch",
        status=status,
    )

    table_configs = tables if tables is not None else [(1, "T1", 6, 0, True)]
    slot_tables = []

    for slot_table_id, table_number, capacity, occupied, is_available in table_configs:
        table = TableDAO(
            id=slot_table_id,
            table_number=table_number,
            capacity=capacity,
            location="Indoor",
        )

        assignments = []
        if occupied:
            other_booking = ReservationDAO(
                status=ReservationStatus.CONFIRMED.value
            )
            assignments.append(
                ReservationTableAssignmentDAO(
                    assigned_seats=occupied,
                    reservation=other_booking,
                )
            )

        slot_tables.append(
            SlotTableDAO(
                id=slot_table_id,
                slot_id=slot_id,
                table_id=slot_table_id,
                available_seats=capacity,
                is_available=is_available,
                table=table,
                assignments=assignments,
            )
        )

    slot.slot_tables = slot_tables
    return slot


# These three tests cover the existing MH-01 two-hour booking cutoff helper.
# They are retained as regression tests for the shared booking rules, not as
# tests of MH-06's separate 48-hour modification window.
def test_two_hour_booking_cutoff_rejects_less_than_two_hours_before_slot():
    slot = build_slot(days_ahead=7, start_time=time(12, 0))
    current_time = datetime.combine(
        slot.date,
        time(10, 1),
        tzinfo=ZoneInfo("Europe/Rome"),
    )

    with pytest.raises(ConflictError, match="at least 2 hours before"):
        validate_two_hour_rule(slot, current_time=current_time)


def test_two_hour_booking_cutoff_allows_exactly_two_hours_before_slot():
    slot = build_slot(days_ahead=7, start_time=time(12, 0))
    current_time = datetime.combine(
        slot.date,
        time(10, 0),
        tzinfo=ZoneInfo("Europe/Rome"),
    )

    validate_two_hour_rule(slot, current_time=current_time)


def test_two_hour_booking_cutoff_allows_more_than_two_hours_before_slot():
    slot = build_slot(days_ahead=7, start_time=time(12, 0))
    current_time = datetime.combine(
        slot.date,
        time(9, 30),
        tzinfo=ZoneInfo("Europe/Rome"),
    )

    validate_two_hour_rule(slot, current_time=current_time)


def test_reallocation_uses_smallest_single_table_that_fits_party():
    slot = build_slot(
        tables=[
            (1, "T1", 6, 0, True),
            (2, "T2", 4, 0, True),
            (3, "T3", 8, 0, True),
        ]
    )

    allocations = assign_tables_for_party(slot, party_size=4)

    assert len(allocations) == 1
    allocated_table, allocated_seats = allocations[0]
    assert allocated_table.table.table_number == "T2"
    assert allocated_seats == 4


def test_reallocation_can_use_seats_after_old_booking_was_released():
    """The fixture represents the state after the old booking was released."""
    slot_after_release = build_slot(
        tables=[(1, "T1", 6, 2, True)]
    )

    allocations = assign_tables_for_party(
        slot_after_release,
        party_size=4,
    )

    assert len(allocations) == 1
    assert allocations[0][0].table.table_number == "T1"
    assert allocations[0][1] == 4


def test_reallocation_splits_party_across_tables_when_needed():
    slot = build_slot(
        tables=[
            (1, "T1", 4, 0, True),
            (2, "T2", 4, 0, True),
        ]
    )

    allocations = assign_tables_for_party(slot, party_size=6)

    assert len(allocations) == 2
    assert sum(seats for _, seats in allocations) == 6


def test_reallocation_does_not_use_unavailable_tables():
    slot = build_slot(
        tables=[
            (1, "T1", 6, 0, False),
            (2, "T2", 4, 0, True),
        ]
    )

    allocations = assign_tables_for_party(slot, party_size=3)

    assert len(allocations) == 1
    assert allocations[0][0].table.table_number == "T2"
    assert allocations[0][1] == 3


def test_reallocation_rejects_party_when_available_seats_are_insufficient():
    slot = build_slot(
        tables=[
            (1, "T1", 4, 2, True),
            (2, "T2", 2, 1, True),
        ]
    )

    with pytest.raises(ConflictError):
        assign_tables_for_party(slot, party_size=5)
