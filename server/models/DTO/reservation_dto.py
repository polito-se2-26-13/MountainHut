"""DTOs for table reservation and slot availability (MH-44)."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class ReservationCreate(BaseModel):
    """Payload to book a table for a party in a specific time slot."""
    slot_id: int = Field(..., description="ID of the selected time slot")
    party_size: int = Field(..., ge=1, description="Number of people in the party")
    user_id: int = Field(..., description="ID of the hiker making the booking")
    contact_name: str = Field(..., min_length=1, description="Full name of contact hiker")
    contact_email: str = Field(..., min_length=3, description="Email for booking confirmation")
    contact_phone: Optional[str] = Field(None, description="Mobile number")
    special_requirements: Optional[str] = Field(None, description="Dietary requirements, allergies, notes")


class AssignedTableInfo(BaseModel):
    """Details of a table assigned to a reservation."""
    table_id: int
    table_number: str
    location: Optional[str] = None
    assigned_seats: int


class ReservationResponse(BaseModel):
    """Response containing reservation details and confirmation info."""
    id: int
    booking_reference: str
    user_id: int
    slot_id: int
    party_size: int
    special_requirements: Optional[str] = None
    contact_name: str
    contact_email: str
    contact_phone: Optional[str] = None
    status: str
    assigned_tables: List[AssignedTableInfo] = []
    created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SlotAvailabilityResponse(BaseModel):
    """Capacity and availability details for a time slot."""
    slot_id: int
    date: str
    start_time: str
    end_time: str
    meal_type: Optional[str] = None
    status: str
    total_capacity: int
    reserved_seats: int
    remaining_seats: int

