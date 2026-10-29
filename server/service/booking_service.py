"""Core Booking and Capacity Deduction Service (MH-44)."""
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from server.const import SlotStatus, ReservationStatus
from server.models.DAO.user import UserDAO
from server.models.DAO.time_slot import TimeSlotDAO, SlotTableDAO
from server.models.DAO.reservation import ReservationDAO, ReservationTableAssignmentDAO
from server.models.DTO.reservation_dto import ReservationCreate


def get_slot_availability(db: Session, slot_id: int) -> dict:
    """Retrieve slot details and real-time seat availability."""
    slot = db.query(TimeSlotDAO).filter(TimeSlotDAO.id == slot_id).first()
    if not slot:
        raise ValueError(f"Time slot with id {slot_id} not found.")

    return {
        "slot_id": slot.id,
        "date": slot.date.isoformat(),
        "start_time": slot.start_time.strftime("%H:%M"),
        "end_time": slot.end_time.strftime("%H:%M"),
        "meal_type": slot.meal_type,
        "status": slot.status,
        "total_capacity": slot.total_capacity,
        "reserved_seats": slot.reserved_seats,
        "remaining_seats": slot.remaining_seats,
    }


def get_reservation_by_reference(db: Session, reference: str) -> Optional[ReservationDAO]:
    """Find reservation by booking reference."""
    return (
        db.query(ReservationDAO)
        .filter(ReservationDAO.booking_reference == reference)
        .first()
    )


def get_user_reservations(db: Session, user_id: int) -> List[ReservationDAO]:
    """Retrieve all reservations made by a hiker."""
    return (
        db.query(ReservationDAO)
        .filter(ReservationDAO.user_id == user_id)
        .order_by(ReservationDAO.created_at.desc())
        .all()
    )


def assign_tables_for_party(
    slot: TimeSlotDAO, party_size: int
) -> List[Tuple[SlotTableDAO, int]]:
    """
    Allocate seats across available tables for the party.
    Tries single-table fit first (smallest table that fits).
    If no single table has enough seats, allocates across multiple tables.
    """
    # Active tables for this slot with at least 1 free seat
    available_tables = [
        st for st in slot.slot_tables if st.is_available and st.free_seats > 0
    ]

    if not available_tables:
        raise ValueError("No available tables configured for this time slot.")

    # 1. Single-table attempt: smallest table where free_seats >= party_size
    single_fits = [st for st in available_tables if st.free_seats >= party_size]
    if single_fits:
        # Best-fit: choose the table with the smallest free capacity >= party_size
        chosen = min(single_fits, key=lambda st: st.free_seats)
        return [(chosen, party_size)]

    # 2. Multi-table attempt: allocate across tables
    assignments = []
    remaining = party_size

    # Sort descending by free seats to use as few tables as possible
    sorted_tables = sorted(available_tables, key=lambda st: st.free_seats, reverse=True)

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


def create_reservation(db: Session, data: ReservationCreate) -> ReservationDAO:
    """
    Create a new table reservation and deduct capacity (MH-44).
    Validates user, slot status, hiker uniqueness per slot, and available capacity.
    """
    # 1. Validate User
    hiker = db.query(UserDAO).filter(UserDAO.id == data.user_id).first()
    if not hiker:
        raise ValueError(f"User with id {data.user_id} not found.")

    # 2. Validate Time Slot
    slot = db.query(TimeSlotDAO).filter(TimeSlotDAO.id == data.slot_id).first()
    if not slot:
        raise ValueError(f"Time slot with id {data.slot_id} not found.")

    if slot.status != SlotStatus.OPEN.value:
        raise ValueError(f"Time slot is {slot.status} and cannot accept reservations.")

    # 3. Check rule: Only one booking per time slot on a date per hiker
    existing_booking = (
        db.query(ReservationDAO)
        .filter(
            ReservationDAO.user_id == data.user_id,
            ReservationDAO.slot_id == data.slot_id,
            ReservationDAO.status == ReservationStatus.CONFIRMED.value,
        )
        .first()
    )
    if existing_booking:
        raise ValueError("Hiker already has a confirmed booking for this time slot.")

    # 4. Check available capacity (Capacity Deduction constraint)
    if data.party_size > slot.remaining_seats:
        raise ValueError(
            f"Not enough seats available (requested {data.party_size}, remaining {slot.remaining_seats})."
        )

    # 5. Determine table assignments
    table_allocations = assign_tables_for_party(slot, data.party_size)

    # 6. Create Reservation record
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
    db.flush()  # Generate reservation.id for foreign keys

    # 7. Create Table Assignments
    for slot_table, seats in table_allocations:
        assignment = ReservationTableAssignmentDAO(
            reservation_id=reservation.id,
            slot_table_id=slot_table.id,
            assigned_seats=seats,
        )
        db.add(assignment)

    try:
        db.commit()
        db.refresh(reservation)
    except IntegrityError as e:
        db.rollback()
        raise ValueError(f"Failed to create reservation due to database constraint: {e}")

    return reservation
