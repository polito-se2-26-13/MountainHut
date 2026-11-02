from sqlalchemy import Column, Integer, String, Enum
from server.models.enum.user_type import UserType
from server.database import Base


class UserDAO(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(100), nullable=False, unique=True)
    password = Column(String, nullable=False) #hashata
    salt= Column(String(32),nullable=False)
    name= Column(String(20),nullable=False)
    surname= Column(String(20),nullable=False)
    phone=Column(String(15))
    role= Column(Enum(UserType), nullable=False)
