from pydantic import BaseModel, EmailStr,Field
from pydantic_extra_types.phone_numbers import PhoneNumber
from typing import Optional
from server.models.enum.user_type import UserType

class UserDTO(BaseModel):
    id: Optional[int] = None
    email: EmailStr= Field(min_length=5, max_length=100)
    password: str
    role: UserType
    firstName: str =Field(min_length=1, max_length=100)
    lastName: str=Field(min_length=1, max_length=100)
    phone: Optional[PhoneNumber]= None

class UserLoginDTO(BaseModel):
    username: str
    password: str

class UserResponseDTO(BaseModel):
    id: int

class UserCreateDTO(BaseModel):
    email: EmailStr=Field(min_length=5, max_length=100)
    password: str
    role: UserType
    firstName: str =Field(min_length=1, max_length=100)
    lastName: str=Field(min_length=1, max_length=100)
    phone: Optional[PhoneNumber]= None

class UserDetailDTO(BaseModel):
    id: Optional[int] = None
    email: EmailStr=Field(min_length=5, max_length=100)
    role: UserType
    firstName: str =Field(min_length=1, max_length=100)
    lastName: str=Field(min_length=1, max_length=100)
    phone: Optional[PhoneNumber]= None

class UserLoginResponse(BaseModel):
    token: str
    #type: str="bearer"
    user: UserDetailDTO
