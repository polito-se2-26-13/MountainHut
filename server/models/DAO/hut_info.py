"""Hut Profile & Facilities database model."""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from server.database import Base


class HutInfoDAO(Base):
    """General information, location, rules, and facilities for the mountain hut."""
    __tablename__ = "hut_info"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    altitude_m: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    how_to_reach: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    points_of_interest: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    has_ebike_charging: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "location": self.location,
            "altitudeM": self.altitude_m,
            "howToReach": self.how_to_reach,
            "pointsOfInterest": self.points_of_interest,
            "contactEmail": self.contact_email,
            "contactPhone": self.contact_phone,
            "hasEbikeCharging": self.has_ebike_charging,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<HutInfoDAO(id={self.id}, name='{self.name}')>"

