from pydantic import BaseModel, EmailStr, Field
from datetime import date, time, datetime
from server.models.enum.meal_type import MealType
class Table(BaseModel):
    tableNumber:str
    seats: int

class SlotResponse(BaseModel):
    slotId: int
    date:date
    startTime: str
    endTime: str
    mealType: MealType
    tables:list[Table]
    message:str

class SlotCreation(BaseModel):
    date: date
    startTime: str
    endTime: str
    mealType: MealType
    tables: list[Table]

class SlotDetail(BaseModel):
    slotId: int
    date:date
    startTime: str
    endTime: str
    mealType: MealType
    tables:list[Table]