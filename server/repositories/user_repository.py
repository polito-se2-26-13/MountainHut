from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from server.models.enum.user_type import UserType
from server.models.DTO.user_dto import UserCreateDTO
from server.models.DAO.user_dao import UserDAO
from server.utils import throw_conflict_if_found, find_or_throw_not_found
from server.database import AsyncSessionLocal
from typing import Optional


class UserRepository:

    def __init__(self, session: Optional[AsyncSession] = None):
        self._session = session

    async def _get_session(self) -> AsyncSession:
        return self._session or AsyncSessionLocal()

    async def create_user(self, user:UserCreateDTO,passHash:str,salt:str) -> UserDAO:
        """
        Create user or throw ConflictError if email exists
        """
        async with await self._get_session() as session:
            userDao = UserDAO(
                email=user.email,
                password=passHash,
                salt=salt,
                name=user.name,
                surname=user.surname,
                phone=user.phone,
                role=user.role
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
                result = await session.execute(select(UserDAO).filter(UserDAO.email == email))
                users = result.scalars().first()
                return users

'''
    async def get_user(self, user_id: int) -> UserDAO | None:
        """
        Get user by id or throw NotFoundError if not found
        """
        async with await self._get_session() as session:
            user = await session.get(UserDAO, user_id)
            return find_or_throw_not_found(
                [user] if user else [],
                lambda _: True,
                f"User with id '{user_id}' not found"
            )


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

    async def delete_user(self, user_id: int) -> bool:
        """
        Delete user by id. Will throw NotFoundError if user doesn't exist
        """
        async with await self._get_session() as session:
            user = await session.get(UserDAO, user_id)

            find_or_throw_not_found(
                [user] if user else [],
                lambda _: True,
                f"User with id '{user_id}' not found"
            )

            await session.delete(user)
            await session.commit()
            return True
'''