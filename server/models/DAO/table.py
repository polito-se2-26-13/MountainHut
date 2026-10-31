"""Hut table model."""
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import String, Integer, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.database import Base

if TYPE_CHECKING:
    from server.models.DAO.time_slot import SlotTableDAO


class TableDAO(Base):
    """Physical dining table in the mountain hut."""
    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    table_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # Indoor, Terrace, etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationship to slot-specific availability configurations
    slot_tables: Mapped[List["SlotTableDAO"]] = relationship(
        "SlotTableDAO", back_populates="table", cascade="all, delete-orphan", lazy="selectin"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tableNumber": self.table_number,
            "capacity": self.capacity,
            "location": self.location,
            "isActive": self.is_active,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<TableDAO(id={self.id}, table_number='{self.table_number}', capacity={self.capacity})>"
