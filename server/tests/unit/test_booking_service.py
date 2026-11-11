"""Tests for MH-44 Core Booking and Capacity Deduction, through the controller and the API."""
import asyncio

import pytest
from datetime import date, time, timedelta
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from server.controllers.reservation_controller import ReservationController, send_confirmation_with_retry
from server.database import AsyncSessionLocal, Base, engine as real_engine, set_sqlite_pragma
from server.main import app
from server.const import SlotStatus, ReservationStatus, UserRole
from server.models.DAO import UserDAO, TableDAO, TimeSlotDAO, SlotTableDAO, ReservationDAO
from server.models.DTO.reservation_dto import ReservationCreate, ReservationMailDTO
from server.models.error.conflict_error import ConflictError
from server.repositories.reservation_repository import ReservationRepository
from server.service.booking_service import get_slot_availability
from server.service.email_service import format_booking_email_html, format_booking_email_text


@pytest.fixture
async def test_db():
    """In-memory SQLite session with sample slot and tables."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool)
    event.listen(engine.sync_engine, "connect", set_sqlite_pragma)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    TestingSession = async_sessionmaker(engine, expire_on_commit=False)

    # Create hiker user
    hiker = UserDAO(
        id=1,
        email="hiker@test.com",
        password_hash="dummy",
        first_name="Alice",
        last_name="Walker",
        phone="+39 340 1112233",
        role=UserRole.HIKER.value,
    )
    # Create tables
    t1 = TableDAO(id=1, table_number="T1", capacity=6, location="Indoor")
    t2 = TableDAO(id=2, table_number="T2", capacity=4, location="Indoor")
    # Create open slot
    slot = TimeSlotDAO(
        id=1,
        date=date.today() + timedelta(days=7),
        start_time=time(12, 30),
        end_time=time(13, 30),
        meal_type="Lunch",
        status=SlotStatus.OPEN.value,
    )
    # Attach tables to slot (total 10 seats)
    st1 = SlotTableDAO(id=1, slot_id=1, table_id=1, available_seats=6)
    st2 = SlotTableDAO(id=2, slot_id=1, table_id=2, available_seats=4)

    async with TestingSession() as seed:
        seed.add_all([hiker, t1, t2, slot, st1, st2])
        await seed.commit()

    # the repositories open their sessions from AsyncSessionLocal, so they use this database now
    AsyncSessionLocal.configure(bind=engine)
    async with TestingSession() as session:
        yield session
    AsyncSessionLocal.configure(bind=real_engine)
    await engine.dispose()


@pytest.fixture
async def client(test_db):
    """HTTP client on the app in the same event loop, on the database of the test_db fixture."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http:
        yield http


async def test_core_booking_and_capacity_deduction(test_db):
    """Test successful booking and automatic capacity deduction (MH-44)."""
    # Check initial availability
    avail_before = await get_slot_availability(test_db, slot_id=1)
    assert avail_before["total_capacity"] == 10
    assert avail_before["reserved_seats"] == 0
    assert avail_before["remaining_seats"] == 10

    # Book 4 seats
    payload = ReservationCreate(
        slot_id=1,
        party_size=4,
        user_id=1,
        contact_name="Alice Walker",
        contact_email="hiker@test.com",
        contact_phone="+39 340 1112233",
        special_requirements="No peanuts",
    )
    res = await ReservationController().create_reservation(payload)

    assert res.id is not None
    assert res.booking_reference.startswith("MH-")
    assert res.party_size == 4
    assert res.status == ReservationStatus.CONFIRMED.value
    assert len(res.assigned_tables) == 1
    assert res.assigned_tables[0].assigned_seats == 4

    # Check capacity after deduction
    avail_after = await get_slot_availability(test_db, slot_id=1)
    assert avail_after["reserved_seats"] == 4
    assert avail_after["remaining_seats"] == 6


async def test_capacity_exceeded_rejected(test_db):
    """Test booking is rejected when party exceeds remaining capacity (MH-44)."""
    # Attempt to book 11 seats when capacity is 10
    payload = ReservationCreate(
        slot_id=1,
        party_size=11,
        user_id=1,
        contact_name="Alice Walker",
        contact_email="hiker@test.com",
    )
    with pytest.raises(ConflictError, match="Not enough seats available"):
        await ReservationController().create_reservation(payload)


async def test_one_booking_per_hiker_per_slot(test_db):
    """Test constraint: only one booking per time slot on a date per hiker."""
    payload1 = ReservationCreate(
        slot_id=1,
        party_size=2,
        user_id=1,
        contact_name="Alice Walker",
        contact_email="hiker@test.com",
    )
    await ReservationController().create_reservation(payload1)

    payload2 = ReservationCreate(
        slot_id=1,
        party_size=2,
        user_id=1,
        contact_name="Alice Walker",
        contact_email="hiker@test.com",
    )
    with pytest.raises(ConflictError, match="already has a confirmed booking"):
        await ReservationController().create_reservation(payload2)


async def test_closed_slot_rejected(test_db):
    """Test booking is rejected if slot is closed."""
    slot = (await test_db.execute(select(TimeSlotDAO).filter_by(id=1))).scalar_one()
    slot.status = SlotStatus.CLOSED.value
    await test_db.commit()

    payload = ReservationCreate(
        slot_id=1,
        party_size=2,
        user_id=1,
        contact_name="Alice Walker",
        contact_email="hiker@test.com",
    )
    with pytest.raises(ConflictError, match="time slot is not open"):
        await ReservationController().create_reservation(payload)


async def test_api_booking_endpoint_flow(client):
    """Test POST /api/reservations and GET /api/reservations/{ref}."""
    # 1. Post reservation
    response = await client.post(
        "/api/reservations",
        json={
            "slot_id": 1,
            "party_size": 3,
            "user_id": 1,
            "contact_name": "Alice Walker",
            "contact_email": "hiker@test.com",
            "contact_phone": "+39 340 1112233",
            "special_requirements": "Gluten-free bread",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "booking_reference" in data
    ref = data["booking_reference"]
    assert data["party_size"] == 3
    assert len(data["assigned_tables"]) > 0

    # 2. Check slot availability reflects the deduction
    avail_res = await client.get("/api/slots/1/availability")
    assert avail_res.status_code == 200
    assert avail_res.json()["remaining_seats"] == 7

    # 3. Retrieve reservation by reference
    get_res = await client.get(f"/api/reservations/{ref}")
    assert get_res.status_code == 200
    assert get_res.json()["booking_reference"] == ref
    assert get_res.json()["special_requirements"] == "Gluten-free bread"


async def test_confirmation_email_follows_the_product_owner(test_db, monkeypatch):
    """MH-03 and issue #24: the name of the hiker who booked and the details, no table numbers."""
    sent = []
    monkeypatch.setattr(
        "server.controllers.reservation_controller.send_booking_confirmation_email",
        lambda mail: sent.append(mail) or {"status": "SENT"},
    )
    payload = ReservationCreate(
        slot_id=1,
        party_size=4,
        user_id=1,
        contact_name="Somebody Else",
        contact_email="other@example.com",
        special_requirements="Gluten-free bread",
    )

    res = await ReservationController().create_reservation(payload)

    assert sent[0].contact_email == "other@example.com"
    for body in (format_booking_email_text(sent[0]), format_booking_email_html(sent[0])):
        assert "Alice Walker" in body
        assert "Somebody Else" not in body
        assert res.booking_reference in body
        assert (date.today() + timedelta(days=7)).strftime("%d/%m/%Y") in body
        assert "12:30-13:30" in body
        assert "4 person(s)" in body
        assert "Gluten-free bread" in body
        assert "T1" not in body and "T2" not in body
        assert "Assigned" not in body and "adjacent" not in body and "2 hours" not in body


def test_confirmation_email_without_requirements_says_so():
    mail = ReservationMailDTO(
        hiker_name="Alice Walker",
        booking_reference="MH-1",
        contact_email="alice@example.com",
        date_str="01/12/2026",
        time_slot="12:30-13:30",
        party_size=2,
        special_reqs=None,
    )

    assert "None specified" in format_booking_email_text(mail)
    assert "None specified" in format_booking_email_html(mail)


async def test_two_bookings_at_the_same_moment_cannot_take_more_seats_than_the_slot_has(test_db):
    test_db.add(UserDAO(id=2, email="bob@test.com", password_hash="dummy", first_name="Bob", last_name="Brown", role=UserRole.HIKER.value))
    await test_db.commit()
    # two groups of 6 on a slot with 10 seats, sent together
    payloads = [ReservationCreate(slot_id=1, party_size=6, user_id=user, contact_name="Group", contact_email=f"g{user}@test.com") for user in (1, 2)]

    results = await asyncio.gather(*(ReservationController().create_reservation(p) for p in payloads), return_exceptions=True)

    assert sum(isinstance(r, ConflictError) for r in results) == 1
    assert (await ReservationRepository().get_slot_availability(1))["reserved_seats"] == 6


def test_html_typed_by_the_user_reaches_the_mail_as_text():
    mail = ReservationMailDTO(
        hiker_name="<b>Alice</b>",
        booking_reference="MH-1",
        contact_email="alice@example.com",
        date_str="01/12/2026",
        time_slot="12:30-13:30",
        party_size=2,
        special_reqs="<a href='http://evil.example'>win</a>",
    )

    html = format_booking_email_html(mail)

    assert "<b>Alice</b>" not in html and "&lt;b&gt;Alice&lt;/b&gt;" in html
    assert "<a href" not in html and "&lt;a href" in html


def test_confirmation_is_tried_again_and_then_only_logged(monkeypatch, capsys):
    mail = ReservationMailDTO(
        hiker_name="Alice Walker", booking_reference="MH-1", contact_email="alice@example.com",
        date_str="01/12/2026", time_slot="12:30-13:30", party_size=2,
    )
    answers = [{"status": "FAILED", "error": "down"}, {"status": "FAILED", "error": "down"}, {"status": "SENT"}]
    calls = []
    monkeypatch.setattr(
        "server.controllers.reservation_controller.send_booking_confirmation_email",
        lambda m: calls.append(m) or answers[len(calls) - 1],
    )

    send_confirmation_with_retry(mail, waits=(0, 0))
    assert len(calls) == 3
    assert "not sent" not in capsys.readouterr().out

    # a mail server that never answers: three tries, then the error in the log
    calls.clear()
    answers[2] = {"status": "FAILED", "error": "down"}
    send_confirmation_with_retry(mail, waits=(0, 0))
    assert len(calls) == 3
    assert "confirmation email not sent for MH-1: down" in capsys.readouterr().out
