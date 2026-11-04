from pydantic import BaseModel, EmailStr, Field
from datetime import date, time, datetime
class Table(BaseModel):
    tableNumber:str
    seats: int

class SlotResponse(BaseModel):
    slotId: int
    date:date
    startTime: str
    endTime: str
    mealType: str|None
    tables:list[Table]
    message:str

class SlotCreation(BaseModel):
    date: date
    startTime: time
    endTime: time
    mealType: str|None=None
    tables: list[Table]

class SlotDetail(BaseModel):
    slotId: int
    date:date
    startTime: str
    endTime: str
    mealType: str|None
    tables:list[Table]