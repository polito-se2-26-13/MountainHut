"""Core Booking, Table Splitting, and Two-Hour Rule Async Service (MH-44 & MH-42)."""
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo
from server.models.DAO.time_slot import TimeSlotDAO, SlotTableDAO
from server.models.error.conflict_error import ConflictError

def validate_two_hour_rule(
    slot: TimeSlotDAO, current_time: Optional[datetime] = None
) -> None:
    """
    Validate MH-01 / MH-42 constraint:
    A hiker can reserve a seat up to 2 hours before the due time.
    """
    italy_tz = ZoneInfo("Europe/Rome")
    now = current_time or datetime.now(italy_tz)
    slot_datetime = datetime.combine(
        slot.date,
        slot.start_time,
        tzinfo=italy_tz
    )
    cutoff = slot_datetime - timedelta(hours=2)

    if now > cutoff:
        raise ConflictError(
            f"Reservations must be made at least 2 hours before the time slot. "
            f"Cutoff was {cutoff.strftime('%Y-%m-%d %H:%M')}, current time is {now.strftime('%Y-%m-%d %H:%M')}."
        )

def assign_tables_for_party(
    slot: TimeSlotDAO, party_size: int
) -> List[Tuple[SlotTableDAO, int]]:
    """
    Allocate seats across available tables for the party (MH-01 & MH-42).

    Rules:
    1. Keep party together as far as possible: try to seat the whole party at
       one table, possibly sharing it with other parties, occupying the smallest
       available set of seats on a table.
    2. Split the party only when no single table has enough free seats.
       When splitting, use as few tables as possible, occupying the smallest
       available set of seats on a table.
    """
    available_tables = [
        st for st in slot.slot_tables if st.is_available and st.free_seats > 0
    ]

    if not available_tables:
        raise ConflictError("No available tables configured for this time slot.")

    # 1. Single table attempt (Keep party together):
    single_fits = [st for st in available_tables if st.free_seats >= party_size]
    if single_fits:
        chosen = min(
            single_fits,
            key=lambda st: (st.free_seats, st.table.capacity if st.table else 0),
        )
        return [(chosen, party_size)]

    # 2. Split party across tables (only when no single table can fit party):
    # the largest tables first give the minimum number of tables needed
    sorted_tables = sorted(available_tables, key=lambda st: st.free_seats, reverse=True)
    needed = next(
        (n for n in range(2, len(sorted_tables) + 1)
         if sum(st.free_seats for st in sorted_tables[:n]) >= party_size),
        None,
    )
    if needed is None:
        raise ConflictError(
            f"Unable to seat party of {party_size}. Not enough free seats on the tables."
        )

    # Best-fit: among the sets of that many tables, the one with the fewest free seats.
    # Trying every set took forever with many tables (a party of 20 on 200 tables of 2 blocked the server),
    # so the sets are built one table at a time: sets[k][total] is one set of k tables with total free seats.
    # Every total stays below party_size + the largest table, so each sets[k] holds only a few entries.
    sets = [{} for _ in range(needed + 1)]
    sets[0][0] = []
    for st in available_tables:
        seats = st.free_seats
        for k in range(needed - 1, -1, -1):  # backwards, so each table enters a set at most once
            for total, tables in list(sets[k].items()):
                if total + seats not in sets[k + 1]:
                    sets[k + 1][total + seats] = tables + [st]
    chosen = sets[needed][min(total for total in sets[needed] if total >= party_size)]

    assignments: List[Tuple[SlotTableDAO, int]] = []
    remaining = party_size
    for st in sorted(chosen, key=lambda st: st.free_seats, reverse=True):
        seats_to_take = min(st.free_seats, remaining)
        assignments.append((st, seats_to_take))
        remaining -= seats_to_take

    return assignments
