"""Core Booking, Table Splitting, and Two-Hour Rule Async Service (MH-44 & MH-42)."""
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from server.const import SlotStatus, ReservationStatus
from server.models.DAO.user import UserDAO
from server.models.DAO.time_slot import TimeSlotDAO, SlotTableDAO
from server.models.DAO.reservation import ReservationDAO, ReservationTableAssignmentDAO
from server.models.DTO.reservation_dto import ReservationCreate


def validate_two_hour_rule(
    slot: TimeSlotDAO, current_time: Optional[datetime] = None
) -> None:
    """
    Validate MH-01 / MH-42 constraint:
    A hiker can reserve a seat up to 2 hours before the due time.
    """
    now = current_time or datetime.now()
    slot_datetime = datetime.combine(slot.date, slot.start_time)
    cutoff = slot_datetime - timedelta(hours=2)

    if now > cutoff:
        raise ValueError(
            f"Reservations must be made at least 2 hours before the time slot. "
            f"Cutoff was {cutoff.strftime('%Y-%m-%d %H:%M')}, current time is {now.strftime('%Y-%m-%d %H:%M')}."
        )


async def get_slot_availability(db: AsyncSession, slot_id: int) -> dict:
    """Retrieve slot details and real-time seat availability asynchronously."""
    result = await db.execute(select(TimeSlotDAO).where(TimeSlotDAO.id == slot_id))
    slot = result.scalar_one_or_none()
    if not slot:
        raise ValueError(f"Time slot with id {slot_id} not found.")

    # Calculate capacity and reservations via direct SQL for accuracy
    cap_res = await db.execute(
        select(func.coalesce(func.sum(SlotTableDAO.available_seats), 0)).where(
            SlotTableDAO.slot_id == slot_id,
            SlotTableDAO.is_available == True,
        )
    )
    total_capacity = int(cap_res.scalar_one())

    res_count = await db.execute(
        select(func.coalesce(func.sum(ReservationDAO.party_size), 0)).where(
            ReservationDAO.slot_id == slot_id,
            ReservationDAO.status == ReservationStatus.CONFIRMED.value,
        )
    )
    reserved_seats = int(res_count.scalar_one())
    remaining_seats = max(0, total_capacity - reserved_seats)

    return {
        "slot_id": slot.id,
        "date": slot.date.isoformat(),
        "start_time": slot.start_time.strftime("%H:%M"),
        "end_time": slot.end_time.strftime("%H:%M"),
        "meal_type": slot.meal_type,
        "status": slot.status,
        "total_capacity": total_capacity,
        "reserved_seats": reserved_seats,
        "remaining_seats": remaining_seats,
    }


async def get_reservation_by_reference(
    db: AsyncSession, reference: str
) -> Optional[ReservationDAO]:
    """Find reservation by booking reference asynchronously."""
    result = await db.execute(
        select(ReservationDAO).where(ReservationDAO.booking_reference == reference)
    )
    return result.scalar_one_or_none()


async def get_user_reservations(
    db: AsyncSession, user_id: int
) -> List[ReservationDAO]:
    """Retrieve all reservations made by a hiker asynchronously."""
    result = await db.execute(
        select(ReservationDAO)
        .where(ReservationDAO.user_id == user_id)
        .order_by(ReservationDAO.created_at.desc())
    )
    return list(result.scalars().all())


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
        raise ValueError("No available tables configured for this time slot.")

    # 1. Single table attempt (Keep party together):
    single_fits = [st for st in available_tables if st.free_seats >= party_size]
    if single_fits:
        chosen = min(
            single_fits,
            key=lambda st: (st.free_seats, st.table.capacity if st.table else 0),
        )
        return [(chosen, party_size)]

    # 2. Split party across tables (only when no single table can fit party):
    sorted_tables = sorted(
        available_tables,
        key=lambda st: (st.free_seats, -(st.table.capacity if st.table else 0)),
        reverse=True,
    )

    assignments: List[Tuple[SlotTableDAO, int]] = []
    remaining = party_size

    for st in sorted_tables:
        if remaining <= 0:
            break
        seats_to_take = min(st.free_seats, remaining)
        assignments.append((st, seats_to_take))
        remaining -= seats_to_take

    if remaining > 0:
        raise ValueError(
            f"Unable to seat party of {party_size}. Remaining unseated: {remaining}."
        )

    return assignments


async def create_reservation(
    db: AsyncSession,
    data: ReservationCreate,
    current_time: Optional[datetime] = None,
) -> ReservationDAO:
    """
    Create a new table reservation and deduct capacity asynchronously.
    Enforces user existence, slot status, 2-hour rule (MH-42),
    one-booking rule (MH-01), capacity check, and table assignment.
    """
    # 1. Validate User
    result = await db.execute(select(UserDAO).where(UserDAO.id == data.user_id))
    hiker = result.scalar_one_or_none()
    if not hiker:
        raise ValueError(f"User with id {data.user_id} not found.")

    # 2. Validate Time Slot
    result = await db.execute(select(TimeSlotDAO).where(TimeSlotDAO.id == data.slot_id))
    slot = result.scalar_one_or_none()
    if not slot:
        raise ValueError(f"Time slot with id {data.slot_id} not found.")

    if slot.status != SlotStatus.OPEN.value:
        raise ValueError(f"Time slot is {slot.status} and cannot accept reservations.")

    # 3. Validate Two-Hour Cutoff Rule (MH-42)
    validate_two_hour_rule(slot, current_time=current_time)

    # 4. Check rule: Only one booking per time slot on a date per hiker
    existing_booking_res = await db.execute(
        select(ReservationDAO).where(
            ReservationDAO.user_id == data.user_id,
            ReservationDAO.slot_id == data.slot_id,
            ReservationDAO.status == ReservationStatus.CONFIRMED.value,
        )
    )
    if existing_booking_res.scalar_one_or_none():
        raise ValueError("Hiker already has a confirmed booking for this time slot.")

    # 5. Check available capacity (Capacity Deduction constraint)
    avail = await get_slot_availability(db, data.slot_id)
    if data.party_size > avail["remaining_seats"]:
        raise ValueError(
            f"Not enough seats available (requested {data.party_size}, remaining {avail['remaining_seats']})."
        )

    # 6. Determine table assignments (single table fit or split across tables)
    table_allocations = assign_tables_for_party(slot, data.party_size)

    # 7. Create Reservation record
    reservation = ReservationDAO(
        user_id=data.user_id,
        slot_id=data.slot_id,
        party_size=data.party_size,
        special_requirements=data.special_requirements,
        contact_name=data.contact_name,
        contact_email=data.contact_email,
        contact_phone=data.contact_phone,
        status=ReservationStatus.CONFIRMED.value,
    )
    db.add(reservation)
    await db.flush()

    # 8. Create Table Assignments
    for slot_table, seats in table_allocations:
        assignment = ReservationTableAssignmentDAO(
            reservation_id=reservation.id,
            slot_table_id=slot_table.id,
            assigned_seats=seats,
        )
        db.add(assignment)

    try:
        await db.commit()
        await db.refresh(reservation)
    except IntegrityError as e:
        await db.rollback()
        raise ValueError(f"Failed to create reservation due to database constraint: {e}")

    return reservation
