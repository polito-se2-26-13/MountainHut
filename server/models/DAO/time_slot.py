"""Time slot and slot-table capacity models."""
from datetime import date, time, datetime
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    Date,
    Time,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.database import Base
from server.const import SlotStatus

if TYPE_CHECKING:
    from server.models.DAO.user import UserDAO
    from server.models.DAO.table import TableDAO
    from server.models.DAO.reservation import ReservationDAO, ReservationTableAssignmentDAO


class TimeSlotDAO(Base):
    """Flexible meal service time slot defined by hut staff (MH-02)."""
    __tablename__ = "time_slots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    meal_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g. Lunch, Dinner
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=SlotStatus.OPEN.value)
    notes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_by_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships with eager selectin loading for async operations
    creator: Mapped[Optional["UserDAO"]] = relationship("UserDAO", back_populates="created_slots", lazy="selectin")
    slot_tables: Mapped[List["SlotTableDAO"]] = relationship(
        "SlotTableDAO", back_populates="slot", cascade="all, delete-orphan", lazy="selectin"
    )
    reservations: Mapped[List["ReservationDAO"]] = relationship(
        "ReservationDAO", back_populates="slot", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def total_capacity(self) -> int:
        """Total configured seats across all available tables for this slot."""
        return sum(st.available_seats for st in self.slot_tables if st.is_available)

    @property
    def reserved_seats(self) -> int:
        """Total seats currently reserved in confirmed reservations for this slot."""
        from server.const import ReservationStatus
        return sum(
            res.party_size
            for res in self.reservations
            if res.status == ReservationStatus.CONFIRMED.value
        )

    @property
    def remaining_seats(self) -> int:
        """Available seats left to be booked."""
        return max(0, self.total_capacity - self.reserved_seats)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "startTime": self.start_time.strftime("%H:%M") if self.start_time else None,
            "endTime": self.end_time.strftime("%H:%M") if self.end_time else None,
            "mealType": self.meal_type,
            "status": self.status,
            "notes": self.notes,
            "createdById": self.created_by_id,
            "totalCapacity": self.total_capacity,
            "reservedSeats": self.reserved_seats,
            "remainingSeats": self.remaining_seats,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return (
            f"<TimeSlotDAO(id={self.id}, date={self.date}, "
            f"time={self.start_time}-{self.end_time}, status='{self.status}')>"
        )


class SlotTableDAO(Base):
    """Specific table and seat allocation configured for a time slot (MH-02)."""
    __tablename__ = "slot_tables"
    __table_args__ = (
        UniqueConstraint("slot_id", "table_id", name="uq_slot_table"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slot_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("time_slots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    table_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tables.id", ondelete="CASCADE"), nullable=False, index=True
    )
    available_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships with eager selectin loading for async operations
    slot: Mapped["TimeSlotDAO"] = relationship("TimeSlotDAO", back_populates="slot_tables", lazy="selectin")
    table: Mapped["TableDAO"] = relationship("TableDAO", back_populates="slot_tables", lazy="selectin")
    assignments: Mapped[List["ReservationTableAssignmentDAO"]] = relationship(
        "ReservationTableAssignmentDAO", back_populates="slot_table", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def occupied_seats(self) -> int:
        """Sum of seats occupied by confirmed reservations at this table for this slot."""
        from server.const import ReservationStatus
        return sum(
            assignment.assigned_seats
            for assignment in self.assignments
            if assignment.reservation.status == ReservationStatus.CONFIRMED.value
        )

    @property
    def free_seats(self) -> int:
        """Remaining free seats at this table for sharing."""
        return max(0, self.available_seats - self.occupied_seats)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "slotId": self.slot_id,
            "tableId": self.table_id,
            "tableNumber": self.table.table_number if self.table else None,
            "tableLocation": self.table.location if self.table else None,
            "availableSeats": self.available_seats,
            "occupiedSeats": self.occupied_seats,
            "freeSeats": self.free_seats,
            "isAvailable": self.is_available,
        }

    def __repr__(self) -> str:
        return (
            f"<SlotTableDAO(id={self.id}, slot_id={self.slot_id}, "
            f"table_id={self.table_id}, available_seats={self.available_seats})>"
        )
