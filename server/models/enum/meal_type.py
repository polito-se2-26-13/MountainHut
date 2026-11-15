from enum import Enum
"""Type of meal in our system"""
class MealType(str,Enum):
    LUNCH="Lunch"
    DINNER="Dinner"
    SNACK="Snack"
    BREAKFAST="Breakfast"