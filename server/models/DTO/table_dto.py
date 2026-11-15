from pydantic import BaseModel, EmailStr, Field
from datetime import date, time, datetime
from server.models.enum.meal_type import MealType

class TableResponse(BaseModel):
    id:int
    tableNumber:str
    capacity: int
    location: str|None   
    