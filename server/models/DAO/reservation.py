"""Reservation and Table Assignment database models (MH-01 & MH-03)."""
import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String,
    Integer,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.database import Base
from server.const import ReservationStatus


def generate_booking_reference() -> str:
    """Generate a readable, unique booking reference code (MH-03)."""
    return f"MH-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


class ReservationDAO(Base):
    """Hiker table reservation model (MH-01, MH-03)."""
    __tablename__ = "reservations"
    __table_args__ = (
        # MH-01 rule: only one booking per time slot on a date per hiker
        UniqueConstraint("user_id", "slot_id", name="uq_user_slot_reservation"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    booking_reference: Mapped[str] = mapped_column(
        String(32), unique=True, nullable=False, index=True, default=generate_booking_reference
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slot_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("time_slots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    party_size: Mapped[int] = mapped_column(Integer, nullable=False)
    special_requirements: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # e.g., allergies, guide notes, high chairs (MH-03)
    contact_name: Mapped[str] = mapped_column(String(200), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ReservationStatus.CONFIRMED.value
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    hiker: Mapped["UserDAO"] = relationship("UserDAO", back_populates="reservations")
    slot: Mapped["TimeSlotDAO"] = relationship("TimeSlotDAO", back_populates="reservations")
    table_assignments: Mapped[List["ReservationTableAssignmentDAO"]] = relationship(
        "ReservationTableAssignmentDAO",
        back_populates="reservation",
        cascade="all, delete-orphan",
    )

    def to_confirmation_dict(self) -> dict:
        """Returns details needed for booking confirmation email / view (MH-03)."""
        assigned_tables = [
            {
                "tableNumber": ta.slot_table.table.table_number,
                "tableLocation": ta.slot_table.table.location,
                "seatsAssigned": ta.assigned_seats,
            }
            for ta in self.table_assignments
            if ta.slot_table and ta.slot_table.table
        ]
        return {
            "bookingReference": self.booking_reference,
            "hikerName": self.contact_name,
            "hikerEmail": self.contact_email,
            "hikerPhone": self.contact_phone,
            "date": self.slot.date.isoformat() if self.slot and self.slot.date else None,
            "timeSlot": (
                f"{self.slot.start_time.strftime('%H:%M')} - {self.slot.end_time.strftime('%H:%M')}"
                if self.slot and self.slot.start_time and self.slot.end_time
                else None
            ),
            "partySize": self.party_size,
            "specialRequirements": self.special_requirements,
            "status": self.status,
            "assignedTables": assigned_tables,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }

    def to_dict(self) -> dict:
        data = self.to_confirmation_dict()
        data["id"] = self.id
        data["userId"] = self.user_id
        data["slotId"] = self.slot_id
        data["updatedAt"] = self.updated_at.isoformat() if self.updated_at else None
        return data

    def __repr__(self) -> str:
        return (
            f"<ReservationDAO(id={self.id}, ref='{self.booking_reference}', "
            f"user_id={self.user_id}, slot_id={self.slot_id}, party_size={self.party_size})>"
        )


class ReservationTableAssignmentDAO(Base):
    """Maps reserved seats across one or more tables in a slot (MH-01 Table Assignment)."""
    __tablename__ = "reservation_table_assignments"
    __table_args__ = (
        UniqueConstraint("reservation_id", "slot_table_id", name="uq_reservation_slot_table"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    reservation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("reservations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slot_table_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("slot_tables.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assigned_seats: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    reservation: Mapped["ReservationDAO"] = relationship(
        "ReservationDAO", back_populates="table_assignments"
    )
    slot_table: Mapped["SlotTableDAO"] = relationship(
        "SlotTableDAO", back_populates="assignments"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "reservationId": self.reservation_id,
            "slotTableId": self.slot_table_id,
            "assignedSeats": self.assigned_seats,
            "tableNumber": (
                self.slot_table.table.table_number
                if self.slot_table and self.slot_table.table
                else None
            ),
        }

    def __repr__(self) -> str:
        return (
            f"<ReservationTableAssignmentDAO(id={self.id}, res_id={self.reservation_id}, "
            f"slot_table_id={self.slot_table_id}, seats={self.assigned_seats})>"
        )

