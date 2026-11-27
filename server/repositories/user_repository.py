from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select, func
from server.models.enum.user_type import UserType
from server.models.DTO.user_dto import UserCreateDTO
from server.models.DAO.user import UserDAO
from server.database import AsyncSessionLocal
from typing import Optional


class UserRepository:

    def __init__(self, session: Optional[AsyncSession] = None):
        self._session = session

    async def _get_session(self) -> AsyncSession:
        return self._session or AsyncSessionLocal()

    async def create_user(self, user:UserCreateDTO,passHash:str) -> UserDAO:
        """
        Create user or throw ConflictError if email exists
        """
        async with await self._get_session() as session:
            userDao = UserDAO(
                email=user.email,
                password_hash=passHash,
                first_name=user.firstName,
                last_name=user.lastName,
                phone=user.phone,
                notes=user.notes,
                emergency_contact=user.emergencyContact,
                role=user.role.value,
                must_change_password=user.must_change_password
            )
            session.add(userDao)
            await session.commit()
            await session.refresh(userDao)
            return userDao
    
    async def get_user_by_email(self, email: str) -> UserDAO | None:
        """
        Get user by email or throw NotFoundError if not found
        """
        async with await self._get_session() as session:
            # capitals do not count, also for accounts saved before the registration made emails lowercase
            result = await session.execute(select(UserDAO).filter(func.lower(UserDAO.email) == email.lower()))
            users = result.scalars().first()
            return users
   
    async def get_user_by_field_hiker(self,name:Optional[str]=None, email: Optional[str]=None, phone: Optional[str]=None) -> list[UserDAO] | None:
            """
            Get user by email name or phone
            """
            async with await self._get_session() as session:
                query= select(UserDAO.id,
                              UserDAO.email,
                              UserDAO.first_name,
                              UserDAO.last_name,
                              UserDAO.phone,
                              UserDAO.emergency_contact,
                              ).where(UserDAO.role==UserType.HIKER)
                
                conditions = []
                if name is not None:
                    conditions.append(
                        UserDAO.first_name.ilike(f"%{name}%")
                    )
                if email is not None:
                    conditions.append(
                        UserDAO.email.ilike(f"%{email}%")
                    )
                if phone is not None:
                    conditions.append(
                        UserDAO.phone.ilike(f"%{phone}%")
                    )
                if conditions:
                    query=query.where(or_(*conditions))              
                
                result = await session.execute(query)
                users = result.all()
                return users

    async def get_user(self, user_id: int) -> UserDAO | None:
        """
        Get user by id or throw NotFoundError if not found
        """
        async with await self._get_session() as session:
            user = await session.get(UserDAO, user_id)
            return user
        
    async def delete_user(self, user_id: int) -> bool:
            """
            Delete user by id
            """
            async with await self._get_session() as session:
                user = await session.get(UserDAO, user_id)
        
                await session.delete(user)
                await session.commit()
                return True

'''
    async def list_users(self) -> list[UserDAO]:
        """Get all users"""
        async with await self._get_session() as session:
            result = await session.execute(select(UserDAO))
            return result.scalars().all()

    async def update_user(self, user_id: int, updated_username: str, password: str, type: UserType) -> UserDAO | None:
        """
        Update user information. Throw NotFoundError if not found or ConflictError if the new username exists
        """
        async with await self._get_session() as session:
            db_user = await session.get(UserDAO, user_id)
            if not db_user:
                return None

            result_conflict = await session.execute(select(UserDAO).filter(UserDAO.id != db_user.id).filter(UserDAO.username == updated_username))
            conflicting_username = result_conflict.scalars().all()
            throw_conflict_if_found(
                conflicting_username,
                lambda _: True,
                f"User with username '{updated_username}' already exists"
            )

            db_user.username = updated_username
            db_user.password = password
            db_user.type = type

            await session.commit()
            await session.refresh(db_user)
            return db_user

'''