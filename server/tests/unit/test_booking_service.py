"""Tests for MH-44 Core Booking and Capacity Deduction, through the controller and the API."""
import pytest
from datetime import date, time, timedelta
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from server.controllers.reservation_controller import ReservationController
from server.database import AsyncSessionLocal, Base, engine as real_engine, set_sqlite_pragma
from server.main import app
from server.const import SlotStatus, ReservationStatus, UserRole
from server.models.DAO import UserDAO, TableDAO, TimeSlotDAO, SlotTableDAO, ReservationDAO
from server.models.DTO.reservation_dto import ReservationCreate
from server.models.error.conflict_error import ConflictError
from server.service.booking_service import get_slot_availability


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
