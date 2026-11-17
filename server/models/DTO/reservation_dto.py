"""DTOs for table reservation and slot availability (MH-44)."""
from typing import Annotated, Optional, List
from pydantic import ConfigDict
from pydantic import BaseModel, EmailStr, Field, StringConstraints
from server.models.DTO.user_dto import Phone, Name
from server.models.DTO.slot_dto import Table


class SpecialRequirementDTO(BaseModel):
    """One requirement for part of the party, with its own allergy flag (MH-05)."""
    has_allergy: bool = False
    # spaces are cut first, as in Name, so a description of only spaces is refused
    description: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]

    model_config = ConfigDict(from_attributes=True)


class ReservationCreate(BaseModel):
    """Payload to book a table for a party in a specific time slot."""
    slot_id: int = Field(..., description="ID of the selected time slot")
    party_size: int = Field(..., ge=1, description="Number of people in the party")
    user_id: Optional[int] = Field(None, description="Ignored by the API, the hiker comes from the login token")
    contact_name: Name = Field(..., description="Full name of contact hiker")
    contact_email: EmailStr = Field(..., min_length=5, max_length=100, description="Email for booking confirmation")
    contact_phone: Optional[Phone] = Field(None, description="Mobile number")
    special_requirements: List[SpecialRequirementDTO] = Field([], description="Dietary requirements and allergies")


class ReservationUpdate(BaseModel):
    """What a hiker can change in a booking (MH-06), sent whole as the change window of the history page does."""
    slot_id: int = Field(..., description="ID of the selected time slot")
    party_size: int = Field(..., ge=1, description="Number of people in the party")
    special_requirements: List[SpecialRequirementDTO] = Field(..., description="Dietary requirements and allergies")


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
    special_requirements: List[SpecialRequirementDTO] = []
    contact_name: str
    contact_email: str
    contact_phone: Optional[str] = None
    status: str
    assigned_tables: List[AssignedTableInfo] = []
    #created_at: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TableLayoutAssignment(BaseModel):
    """Assigned seats breakdown at a specific table for a party (MH-04)."""
    table_number: str
    assigned_seats: int
    location: Optional[str] = None


class TableCapacityInfo(BaseModel):
    """Real-time capacity and occupancy information for a physical table in a slot."""
    table_number: str
    capacity: int
    occupied_seats: int
    free_seats: int
    location: Optional[str] = None


class SlotAvailabilityResponse(BaseModel):
    """Capacity, availability, and table layout details for a time slot (MH-04)."""
    slot_id: int
    date: str
    start_time: str
    end_time: str
    meal_type: Optional[str] = None
    status: str
    total_capacity: int
    reserved_seats: int
    remaining_seats: int
    is_available: bool = True
    party_size: Optional[int] = None
    layout_summary: Optional[str] = None
    layout: Optional[List[TableLayoutAssignment]] = None
    tables: Optional[List[TableCapacityInfo]] = None

class ReservationMailDTO(BaseModel):
    hiker_name:str
    booking_reference: str
    contact_email:str
    date_str: str
    time_slot: str
    party_size: int
    special_reqs: List[SpecialRequirementDTO] = []
    # true for the mail of a change (MH-06), so the hiker sees that the booking was changed
    changed: bool = False