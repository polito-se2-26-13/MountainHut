from pydantic import BaseModel, EmailStr, Field
from datetime import date, time, datetime
from server.models.enum.meal_type import MealType

class TimeResponse(BaseModel):
    id:int
    date:date
    startTime: str
    endTime: str
    mealType: MealType|None 