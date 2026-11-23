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
    mealType: MealType|None=None #TODO for test test_slots_of_a_date_are_listed_as_the_pages_read_them mealType is required
    tables:list[Table]
    message:str

class SlotCreation(BaseModel):
    date: date
    startTime: time
    endTime: time
    mealType: MealType|None=None #TODO for test test_slots_of_a_date_are_listed_as_the_pages_read_them mealType is required
    tables: list[Table]

class SlotDetail(BaseModel):
    slotId: int
    date:date
    startTime: str
    endTime: str
    mealType: MealType |None=None #TODO for test test_slots_of_a_date_are_listed_as_the_pages_read_them mealType is required
    tables:list[Table]