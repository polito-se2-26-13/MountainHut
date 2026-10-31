from pydantic import BaseModel, Field
from typing import Optional
from server.models.enum.user_type import UserType

class UserDTO(BaseModel):
    id: Optional[int] = None
    email: str
    password: Optional[str] = None
    salt: Optional[str]= None
    role: Optional[UserType] = None
    name: str
    surname: str
    mobile: Optional[str]= None

class UserLoginDTO(BaseModel):
    email: str 
    password: str

class UserResponseDTO(BaseModel):
    id: int

class UserCreateDTO(BaseModel):
    email: str
    password: Optional[str] = None
    role: Optional[UserType] = None
    name: str
    surname: str
    phone: Optional[str]= None

class UserLoginResponse(BaseModel):
    token: str
    type: str="bearer"