import jwt
from fastapi import HTTPException, status
from server.config.config import SECRET_KEY, TOKEN_LIFESPAN_HOURS, ALGORITHM
from server.models.DTO.user_dto import UserDTO
from server.repositories.user_repository import UserRepository
from server.models.enum.user_type import UserType
from datetime import datetime, timedelta, timezone
import secrets
from argon2.low_level import hash_secret, Type

def generate_token(user: UserDTO) -> str:
    payload = {
        "sub": user.email,
        "role": user.role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_LIFESPAN_HOURS)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def process_token(auth_header: str, allowed_roles: list[UserType] = []):
    token = extract_bearer_token(auth_header)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        role = payload.get("role")

        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user_repo = UserRepository()
        user_dao = await user_repo.get_user_by_email(email)

        if not user_dao:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

        if allowed_roles and user_dao.type not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient rights")

        return user_dao

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}")


def extract_bearer_token(auth_header: str) -> str:
    if not auth_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No token provided")

    parts = auth_header.split(" ")
    if len(parts) != 2 or parts[0] != "Bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token format")

    return parts[1]

def hash_password (password: str)->tuple[str,str]:
        salt=secrets.token_bytes(16)
        passHash= hash_secret(
                    secret=password.encode("utf-8"),
                    salt=salt,
                    time_cost=3,
                    memory_cost=65536,
                    parallelism=4,
                    hash_len=32,
                    type=Type.ID
                ).decode("utf-8")
        return (passHash,salt.hex())

def verify_password(password:str, hashPassword:str,salt:str):
    passHash= hash_secret(
                        secret=password.encode("utf-8"),
                        salt=bytes.fromhex(salt),
                        time_cost=3,
                        memory_cost=65536,
                        parallelism=4,
                        hash_len=32,
                        type=Type.ID
                    ).decode("utf-8")
    return passHash==hashPassword,