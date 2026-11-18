"""Token rules that no other test checks (MH-01, login of every role).

Registration, login, a valid token, a forged token and a wrong role are tested
through the API in integration/test_auth.py. This file keeps the token format,
the token lifetime, the expired token and the token of a user that no longer exists.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from fastapi import HTTPException

from server.models.DTO.user_dto import UserDTO
from server.models.enum.user_type import UserType
from server.service import auth_service
from server.config.config import SECRET_KEY, ALGORITHM, TOKEN_LIFESPAN_HOURS


# Auth Service: Bearer Token
def test_extract_bearer_token_invalid_format():
    # the only wrong format that gets past FastAPI's HTTPBearer and reaches the app
    with pytest.raises(HTTPException) as exc:
        auth_service.extract_bearer_token("Bearer abc123 extra")

    assert exc.value.status_code == 401
    assert exc.value.detail == "Invalid token format"


# Auth Service: JWT
def test_generate_token_contains_user_information():
    user = UserDTO(
        id=1,
        email="anna@example.com",
        password="hashed_password",
        role=UserType.HIKER,
        firstName="Anna",
        lastName="Li"
    )

    before = datetime.now(timezone.utc)
    token = auth_service.generate_token(user)
    after = datetime.now(timezone.utc)

    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM]
    )

    assert payload["sub"] == "anna@example.com"
    assert payload["role"] == UserType.HIKER.value
    # the token lasts TOKEN_LIFESPAN_HOURS from the moment it is made (exp is in whole seconds)
    lifespan = timedelta(hours=TOKEN_LIFESPAN_HOURS)
    assert int((before + lifespan).timestamp()) - 1 <= payload["exp"] <= int((after + lifespan).timestamp()) + 1


@pytest.mark.asyncio
async def test_process_token_rejects_expired_token():
    expired_payload = {
        "sub": "anna@example.com",
        "role": UserType.HIKER.value,
        "exp": datetime.now(timezone.utc) - timedelta(hours=1)
    }

    expired_token = jwt.encode(
        expired_payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    # the repository is replaced, so a broken expiry check can never reach the real database
    with patch("server.service.auth_service.UserRepository"):
        with pytest.raises(HTTPException) as exc:
            await auth_service.process_token(
                f"Bearer {expired_token}"
            )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Token expired"


@pytest.mark.asyncio
async def test_process_token_rejects_user_not_found():
    """A valid JWT is rejected when its user no longer exists in the database."""
    payload = {
        "sub": "missing@example.com",
        "role": UserType.HIKER.value,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    with patch("server.service.auth_service.UserRepository") as repo_class:
        repo = repo_class.return_value
        repo.get_user_by_email = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc:
            await auth_service.process_token(f"Bearer {token}")

    assert exc.value.status_code == 401
    assert exc.value.detail == "User not found"
    repo.get_user_by_email.assert_awaited_once_with("missing@example.com")
