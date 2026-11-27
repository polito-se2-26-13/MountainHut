"""User / Hiker / Staff database model."""
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from server.database import Base
from server.models.enum.user_type import UserType
from server.utils.security import hash_password, verify_password


class UserDAO(Base):
    """User account model representing Hikers, Employees, and Wardens."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default=UserType.HIKER.value)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # e.g. "registered mountain guide"
    emergency_contact: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    must_change_password: Mapped[bool]=mapped_column(Boolean,default=False,nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # no lists of the user's bookings or slots here: nothing reads them, and loaded with the user
    # on every request with a token they brought along the bookings, slots and tables behind them

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def set_password(self, password: str) -> None:
        self.password_hash = hash_password(password)

    def verify_password(self, password: str) -> bool:
        return verify_password(password, self.password_hash)

    def to_dict(self, include_sensitive: bool = False) -> dict:
        data = {
            "id": self.id,
            "email": self.email,
            "firstName": self.first_name,
            "lastName": self.last_name,
            "fullName": self.full_name,
            "phone": self.phone,
            "role": self.role,
            "notes": self.notes,
            "emergencyContact": self.emergency_contact,
            "isActive": self.is_active,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_sensitive:
            data["passwordHash"] = self.password_hash
        return data

    def __repr__(self) -> str:
        return f"<UserDAO(id={self.id}, email='{self.email}', role='{self.role}')>"
