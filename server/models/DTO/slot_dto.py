from pydantic import BaseModel, EmailStr, Field
from datetime import date, time, datetime
class Table(BaseModel):
    tableNumber:str
    seats: int

class SlotResponse(BaseModel):
    slotid: int
    date:date
    startTime: time
    endTime: time
    mealType: str
    tables:list[Table]
    message:str

class SlotCreation(BaseModel):
    date: date
    startTime: time
    endTime: time
    mealType: str
    tables: list[Table]

class SlotDetail(BaseModel):
    slotid: int
    date:date
    startTime: time
    endTime: time
    mealType: str
    tables:list[Table]