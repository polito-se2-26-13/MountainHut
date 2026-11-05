
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from fastapi import HTTPException

from server.controllers import user_controller as controller_module
from server.controllers.user_controller import UserController
from server.models.DTO.user_dto import UserCreateDTO, UserLoginDTO
from server.models.enum.user_type import UserType
from server.models.error.conflict_error import ConflictError
from server.models.error.notfound_error import NotFoundError
from server.service import auth_service
from server.config.config import SECRET_KEY, ALGORITHM


# Test data
def create_user_dao():
    """Create a fake user DAO without using the database."""
    return SimpleNamespace(
        id=1,
        email="anna@example.com",
        password_hash="hashed_password",
        first_name="Anna",
        last_name="Li",
        phone=None,
        role=UserType.Hiker.value
    )


def create_user_dto():
    return UserCreateDTO(
        email="anna@example.com",
        password="Password123!",
        role=UserType.Hiker,
        firstName="Anna",
        lastName="Li"
    )



# UserController: Registration
@pytest.mark.asyncio
async def test_create_user_success(monkeypatch):
    controller = UserController()
    controller.repo = AsyncMock()

    controller.repo.get_user_by_email.return_value = None
    controller.repo.create_user.return_value = create_user_dao()

    monkeypatch.setattr(
        controller_module,
        "hash_password",
        lambda password: "hashed_password"
    )

    result = await controller.create_user(create_user_dto())

    assert result.id == 1

    controller.repo.get_user_by_email.assert_awaited_once_with(
        "anna@example.com"
    )

    controller.repo.create_user.assert_awaited_once()

    args = controller.repo.create_user.await_args
    assert args.kwargs["passHash"] == "hashed_password"


@pytest.mark.asyncio
async def test_create_user_duplicate_email():
    controller = UserController()
    controller.repo = AsyncMock()

    controller.repo.get_user_by_email.return_value = create_user_dao()

    with pytest.raises(ConflictError):
        await controller.create_user(create_user_dto())

    controller.repo.create_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_user_password_is_hashed(monkeypatch):
    controller = UserController()
    controller.repo = AsyncMock()

    controller.repo.get_user_by_email.return_value = None
    controller.repo.create_user.return_value = create_user_dao()

    hash_mock = lambda password: "secure_hash"

    monkeypatch.setattr(
        controller_module,
        "hash_password",
        hash_mock
    )

    await controller.create_user(create_user_dto())
    controller.repo.create_user.assert_awaited_once()
    args = controller.repo.create_user.await_args

    assert args.kwargs["passHash"] == "secure_hash"
    assert args.kwargs["passHash"] != "Password123!"


@pytest.mark.asyncio
async def test_create_user_propagates_repository_error():
    controller = UserController()
    controller.repo = AsyncMock()

    controller.repo.get_user_by_email.return_value = None

    controller.repo.create_user.side_effect = RuntimeError(
        "Database error"
    )
    with pytest.raises(RuntimeError, match="Database error"):
        await controller.create_user(create_user_dto())
    controller.repo.get_user_by_email.assert_awaited_once_with(
        "anna@example.com"
    )
    controller.repo.create_user.assert_awaited_once()



# UserController: Login
@pytest.mark.asyncio
async def test_login_user_success(monkeypatch):
    controller = UserController()
    controller.repo = AsyncMock()

    controller.repo.get_user_by_email.return_value = create_user_dao()

    monkeypatch.setattr(
        controller_module,
        "verify_password",
        lambda password, hashed: True
    )

    monkeypatch.setattr(
        controller_module,
        "generate_token",
        lambda user: "fake-jwt-token"
    )

    login_data = UserLoginDTO(
        username="anna@example.com",
        password="Password123!"
    )

    result = await controller.login_user(login_data)

    assert result.token == "fake-jwt-token"
    assert result.user.email == "anna@example.com"
    assert result.user.firstName == "Anna"
    assert result.user.role == UserType.Hiker


@pytest.mark.asyncio
async def test_login_user_not_found():
    controller = UserController()
    controller.repo = AsyncMock()

    controller.repo.get_user_by_email.return_value = None

    login_data = UserLoginDTO(
        username="unknown@example.com",
        password="Password123!"
    )

    with pytest.raises(NotFoundError):
        await controller.login_user(login_data)


@pytest.mark.asyncio
async def test_login_user_wrong_password(monkeypatch):
    controller = UserController()
    controller.repo = AsyncMock()

    controller.repo.get_user_by_email.return_value = create_user_dao()

    monkeypatch.setattr(
        controller_module,
        "verify_password",
        lambda password, hashed: False
    )

    login_data = UserLoginDTO(
        username="anna@example.com",
        password="WrongPassword!"
    )

    with pytest.raises(NotFoundError):
        await controller.login_user(login_data)


# Auth Service: Bearer Token
def test_extract_bearer_token_success():
    token = auth_service.extract_bearer_token(
        "Bearer abc123"
    )

    assert token == "abc123"


def test_extract_bearer_token_missing_header():
    with pytest.raises(HTTPException) as exc:
        auth_service.extract_bearer_token(None)

    assert exc.value.status_code == 401


@pytest.mark.parametrize(
    "header",
    [
        "abc123",
        "Basic abc123",
        "Bearer",
        "Bearer abc123 extra"
    ]
)
def test_extract_bearer_token_invalid_format(header):
    with pytest.raises(HTTPException) as exc:
        auth_service.extract_bearer_token(header)

    assert exc.value.status_code == 401


# Auth Service: JWT
def test_generate_token_contains_user_information():
    from server.models.DTO.user_dto import UserDTO

    user = UserDTO(
        id=1,
        email="anna@example.com",
        password="hashed_password",
        role=UserType.Hiker,
        firstName="Anna",
        lastName="Li"
    )

    token = auth_service.generate_token(user)

    payload = jwt.decode(
        token,
        SECRET_KEY,
        algorithms=[ALGORITHM]
    )

    assert payload["sub"] == "anna@example.com"
    assert payload["role"] == UserType.Hiker.value
    assert "exp" in payload


@pytest.mark.asyncio
async def test_process_token_rejects_invalid_token():
    with pytest.raises(HTTPException) as exc:
        await auth_service.process_token("Bearer invalid-token")

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_process_token_rejects_expired_token():
    expired_payload = {
        "sub": "anna@example.com",
        "role": UserType.Hiker.value,
        "exp": datetime.now(timezone.utc) - timedelta(hours=1)
    }

    expired_token = jwt.encode(
        expired_payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    with pytest.raises(HTTPException) as exc:
        await auth_service.process_token(
            f"Bearer {expired_token}"
        )

    assert exc.value.status_code == 401

# Auth Service: Role Permission
@pytest.mark.asyncio
async def test_process_token_rejects_unauthorized_role():
    # Create a valid JWT for a Hiker
    payload = {
        "sub": "anna@example.com",
        "role": UserType.Hiker.value,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    # Mock the database lookup
    fake_user = create_user_dao()

    with patch(
        "server.service.auth_service.UserRepository"
    ) as mock_repo_class:

        mock_repo = mock_repo_class.return_value
        mock_repo.get_user_by_email = AsyncMock(
            return_value=fake_user
        )

        # Hiker is not allowed to access an Employee-only resource
        with pytest.raises(HTTPException) as exc:
            await auth_service.process_token(
                f"Bearer {token}",
                allowed_roles=[UserType.Employee]
            )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Insufficient rights"

@pytest.mark.asyncio
async def test_process_token_accepts_valid_token():
    payload = {
        "sub": "anna@example.com",
        "role": UserType.Hiker.value,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    fake_user = create_user_dao()

    with patch(
        "server.service.auth_service.UserRepository"
    ) as mock_repo_class:

        mock_repo = mock_repo_class.return_value
        mock_repo.get_user_by_email = AsyncMock(
            return_value=fake_user
        )

        result = await auth_service.process_token(
            f"Bearer {token}",
            allowed_roles=[UserType.Hiker]
        )

    assert result == fake_user
    assert result.email == "anna@example.com"

    mock_repo.get_user_by_email.assert_awaited_once_with(
        "anna@example.com"
    )
@pytest.mark.asyncio
async def test_process_token_rejects_user_not_found():
    """A valid JWT is rejected when its user no longer exists in the database."""
    payload = {
        "sub": "missing@example.com",
        "role": UserType.Hiker.value,
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