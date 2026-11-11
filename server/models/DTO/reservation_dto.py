"""DTOs for table reservation and slot availability (MH-44)."""
from typing import Optional, List
from pydantic import ConfigDict
from pydantic import BaseModel, EmailStr, Field
from server.models.DTO.user_dto import Phone
from server.models.DTO.slot_dto import Table

class ReservationCreate(BaseModel):
    """Payload to book a table for a party in a specific time slot."""
    slot_id: int = Field(..., description="ID of the selected time slot")
    party_size: int = Field(..., ge=1, description="Number of people in the party")
    user_id: Optional[int] = Field(None, description="Ignored by the API, the hiker comes from the login token")
    contact_name: str = Field(...,max_length=100, min_length=1, description="Full name of contact hiker")
    contact_email: EmailStr = Field(..., min_length=5, max_length=100, description="Email for booking confirmation")
    contact_phone: Optional[Phone] = Field(None, description="Mobile number")
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
    date: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
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

class ReservationMailDTO(BaseModel):
    hiker_name:str
    booking_reference: str
    contact_email:str
    date_str: str
    time_slot: str
    party_size: int
    special_reqs: Optional[str]= "None specified"