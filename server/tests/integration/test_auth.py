"""Integration tests of registration and login: POST /api/auth/register and POST /api/auth/login,
with the same bodies the frontend sends."""
import asyncio
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

from server.models.DAO.user import UserDAO
from server.models.enum.user_type import UserType
from server.service.auth_service import process_token
from server.utils.security import hash_password

ANNA = {
    "email": "anna@example.com",
    "password": "Password123!",
    "firstName": "Anna",
    "lastName": "Li",
    "phone": "+39 333 1234567",
    "role": "Hiker",
}


def test_registration_saves_the_hiker(client, db):
    response = client.post("/api/auth/register", json=ANNA)

    assert response.status_code == 201
    saved = db.get(UserDAO, response.json()["id"])
    assert saved.email == "anna@example.com"
    assert saved.first_name == "Anna"
    assert saved.last_name == "Li"
    assert saved.role == "Hiker"
    assert saved.password_hash != "Password123!"


def test_phone_without_prefix_is_read_as_italian(client, db):
    response = client.post("/api/auth/register", json={**ANNA, "phone": "333 1234567"})

    assert response.status_code == 201
    assert db.get(UserDAO, response.json()["id"]).phone == "+393331234567"


def test_registration_saves_notes_and_emergency_contact(client, db):
    response = client.post("/api/auth/register", json={**ANNA, "notes": "registered mountain guide", "emergencyContact": "Marco, +39 333 7654321"})

    assert response.status_code == 201
    saved = db.get(UserDAO, response.json()["id"])
    assert saved.notes == "registered mountain guide"
    assert saved.emergency_contact == "Marco, +39 333 7654321"


def test_names_are_saved_without_spaces_around_and_cannot_be_only_spaces(client, db):
    response = client.post("/api/auth/register", json={**ANNA, "firstName": "  Anna ", "lastName": " Li"})

    assert db.get(UserDAO, response.json()["id"]).first_name == "Anna"
    assert client.post("/api/auth/register", json={**ANNA, "email": "spaces@example.com", "firstName": "   "}).status_code == 422


def test_same_email_cannot_register_twice(client):
    client.post("/api/auth/register", json=ANNA)

    assert client.post("/api/auth/register", json=ANNA).status_code == 409


def test_login_returns_token_and_user(client):
    client.post("/api/auth/register", json=ANNA)

    response = client.post("/api/auth/login", json={"username": ANNA["email"], "password": ANNA["password"]})

    assert response.status_code == 200
    body = response.json()
    assert body["token"]
    assert body["user"]["email"] == "anna@example.com"
    assert body["user"]["firstName"] == "Anna"
    assert body["user"]["lastName"] == "Li"
    assert body["user"]["role"] == "Hiker"


def test_wrong_password_is_refused(client):
    client.post("/api/auth/register", json=ANNA)

    response = client.post("/api/auth/login", json={"username": ANNA["email"], "password": "wrong"})

    assert response.status_code == 401
    assert "token" not in response.json()


def test_unknown_user_is_refused(client):
    response = client.post("/api/auth/login", json={"username": "nobody@example.com", "password": "x"})

    assert response.status_code == 401


def test_registration_always_creates_a_hiker(client, db):
    response = client.post("/api/auth/register", json={**ANNA, "role": "Warden"})

    assert response.status_code == 201
    assert db.get(UserDAO, response.json()["id"]).role == "Hiker"


def test_password_needs_at_least_8_characters(client):
    assert client.post("/api/auth/register", json={**ANNA, "password": "Pass123"}).status_code == 422


def test_email_is_the_same_whatever_its_capitals(client):
    client.post("/api/auth/register", json=ANNA)

    assert client.post("/api/auth/register", json={**ANNA, "email": "ANNA@Example.com"}).status_code == 409
    login = client.post("/api/auth/login", json={"username": "Anna@Example.COM", "password": ANNA["password"]})
    assert login.status_code == 200


def test_an_old_account_saved_with_capitals_can_log_in(client, db):
    db.add(UserDAO(email="Mario@Example.com", password_hash=hash_password(ANNA["password"]), first_name="Mario", last_name="R", role="Hiker"))
    db.commit()

    login = client.post("/api/auth/login", json={"username": "mario@example.com", "password": ANNA["password"]})

    assert login.status_code == 200


def test_token_opens_only_the_routes_of_its_role(client):
    client.post("/api/auth/register", json=ANNA)
    token = client.post("/api/auth/login", json={"username": ANNA["email"], "password": ANNA["password"]}).json()["token"]

    assert asyncio.run(process_token(f"Bearer {token}", [UserType.Hiker])).email == ANNA["email"]
    with pytest.raises(HTTPException) as refused:
        asyncio.run(process_token(f"Bearer {token}", [UserType.Employee]))
    assert refused.value.status_code == 403


def test_a_token_signed_with_another_key_is_refused(client):
    # the old key was public on GitHub, so a token signed with any key but ours must open nothing
    client.post("/api/auth/register", json=ANNA)
    forged = jwt.encode({"sub": ANNA["email"], "role": "Hiker", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                        "a key that is not ours but long enough for HS256", algorithm="HS256")

    with pytest.raises(HTTPException) as refused:
        asyncio.run(process_token(f"Bearer {forged}", [UserType.Hiker]))
    assert refused.value.status_code == 401
