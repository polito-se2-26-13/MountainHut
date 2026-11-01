"""Reservation and availability API routes (MH-44)."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from server.database import get_db
from server.models.DTO.reservation_dto import (
    ReservationCreate,
    ReservationResponse,
    AssignedTableInfo,
    SlotAvailabilityResponse,
)
from server.service.booking_service import (
    create_reservation,
    get_reservation_by_reference,
    get_user_reservations,
    get_slot_availability,
)

router = APIRouter(prefix="/api", tags=["Reservations"])


def _to_response_dto(res) -> ReservationResponse:
    assigned_tables = [
        AssignedTableInfo(
            table_id=ta.slot_table.table_id,
            table_number=ta.slot_table.table.table_number,
            location=ta.slot_table.table.location,
            assigned_seats=ta.assigned_seats,
        )
        for ta in res.table_assignments
        if ta.slot_table and ta.slot_table.table
    ]
    return ReservationResponse(
        id=res.id,
        booking_reference=res.booking_reference,
        user_id=res.user_id,
        slot_id=res.slot_id,
        party_size=res.party_size,
        special_requirements=res.special_requirements,
        contact_name=res.contact_name,
        contact_email=res.contact_email,
        contact_phone=res.contact_phone,
        status=res.status,
        assigned_tables=assigned_tables,
        created_at=res.created_at.isoformat() if res.created_at else None,
    )


@router.post("/reservations", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
def book_table(payload: ReservationCreate, db: Session = Depends(get_db)):
    """Book a table for a party in a selected time slot and deduct capacity."""
    try:
        reservation = create_reservation(db, payload)
        return _to_response_dto(reservation)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )


@router.get("/reservations/{reference}", response_model=ReservationResponse)
def get_reservation(reference: str, db: Session = Depends(get_db)):
    """Retrieve reservation details by booking reference (MH-03)."""
    reservation = get_reservation_by_reference(db, reference)
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reservation with reference '{reference}' not found.",
        )
    return _to_response_dto(reservation)


@router.get("/reservations/user/{user_id}", response_model=List[ReservationResponse])
def get_hiker_reservations(user_id: int, db: Session = Depends(get_db)):
    """List all reservations for a given hiker."""
    reservations = get_user_reservations(db, user_id)
    return [_to_response_dto(r) for r in reservations]


@router.get("/slots/{slot_id}/availability", response_model=SlotAvailabilityResponse)
def get_slot_seats(slot_id: int, db: Session = Depends(get_db)):
    """Get remaining and reserved seat capacity for a time slot."""
    try:
        data = get_slot_availability(db, slot_id)
        return SlotAvailabilityResponse(**data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
