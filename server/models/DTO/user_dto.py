from pydantic import BaseModel, EmailStr,Field, StringConstraints
from pydantic_extra_types.phone_numbers import PhoneNumber
from typing import Annotated, Optional
from server.models.enum.user_type import UserType

class Phone(PhoneNumber):
    """A number without prefix, accepted by the registration form, is read as Italian."""
    default_region_code = "IT"
    phone_format = "E164"

# a name typed by a person: the spaces around it are removed, so a name of only spaces is refused
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]

class UserDTO(BaseModel):
    id: Optional[int] = None
    email: EmailStr= Field(min_length=5, max_length=100)
    password: str
    role: UserType
    firstName: str =Field(min_length=1, max_length=100)
    lastName: str=Field(min_length=1, max_length=100)
    phone: Optional[Phone]= None

class UserLoginDTO(BaseModel):
    username: EmailStr=Field(max_length=100)
    password: str

class UserResponseDTO(BaseModel):
    id: int

class UserCreateDTO(BaseModel):
    email: EmailStr=Field(min_length=5, max_length=100)
    password: str=Field(min_length=8)
    role: UserType
    firstName: Name
    lastName: Name
    # for the PO the phone of a hiker is required, notes and emergency contact are optional (issue #22 of the course repository)
    phone: Phone
    notes: Optional[str]=Field(None, max_length=555)
    emergencyContact: Optional[str]=Field(None, max_length=255)

class UserDetailDTO(BaseModel):
    id: Optional[int] = None
    email: EmailStr=Field(min_length=5, max_length=100)
    role: UserType
    firstName: str =Field(min_length=1, max_length=100)
    lastName: str=Field(min_length=1, max_length=100)
    phone: Optional[Phone]= None

class UserLoginResponse(BaseModel):
    token: str
    #type: str="bearer"
    user: UserDetailDTO
