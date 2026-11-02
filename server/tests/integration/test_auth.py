"""Integration tests of registration and login: POST /api/auth/register and POST /api/auth/login,
with the same bodies the frontend sends."""
import asyncio

import pytest
from fastapi import HTTPException

from server.models.DAO.user import UserDAO
from server.models.enum.user_type import UserType
from server.service.auth_service import process_token

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

    assert response.status_code == 404
    assert "token" not in response.json()


def test_unknown_user_is_refused(client):
    response = client.post("/api/auth/login", json={"username": "nobody@example.com", "password": "x"})

    assert response.status_code == 404


def test_token_opens_only_the_routes_of_its_role(client):
    client.post("/api/auth/register", json=ANNA)
    token = client.post("/api/auth/login", json={"username": ANNA["email"], "password": ANNA["password"]}).json()["token"]

    assert asyncio.run(process_token(f"Bearer {token}", [UserType.Hiker])).email == ANNA["email"]
    with pytest.raises(HTTPException) as refused:
        asyncio.run(process_token(f"Bearer {token}", [UserType.Employee]))
    assert refused.value.status_code == 403
