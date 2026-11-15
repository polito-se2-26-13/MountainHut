from enum import Enum

class UserType(str,Enum):
    HIKER="Hiker"
    EMPLOYEE="Employee"
    MENAGER="Manager"
    WARDEN="Warden"