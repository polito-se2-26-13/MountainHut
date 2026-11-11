"""Integration tests of the Define slot capacity story (MH-02): GET and POST /api/slots,
with the same requests the pages send."""
from datetime import date, timedelta

from server.models.DAO.table import TableDAO
from server.models.DAO.time_slot import TimeSlotDAO
from server.models.DAO.user import UserDAO
from server.service.auth_service import generate_token

DAY = (date.today() + timedelta(days=7)).isoformat()
OTHER_DAY = (date.today() + timedelta(days=8)).isoformat()


def login_as(db, role):
    user = UserDAO(email=f"{role.lower()}@example.com", password_hash="x", first_name=role, last_name="Test", role=role)
    db.add(user)
    db.commit()
    return {"Authorization": f"Bearer {generate_token(user)}"}


def slot(tables, day=DAY, start="12:00", end="13:00", **extra):
    return {
        "date": day,
        "startTime": start,
        "endTime": end,
        "tables": [{"tableNumber": number, "seats": seats} for number, seats in tables],
        **extra,
    }


def test_employee_creates_a_new_slot_with_new_tables(client, db):
    employee = login_as(db, "Employee")

    response = client.post("/api/slots", json=slot([("T1", 4), ("T2", 2)], mealType="Lunch"), headers=employee)

    assert response.status_code == 201
    saved = response.json()
    assert saved["slotId"] == db.query(TimeSlotDAO).one().id
    assert saved["date"] == DAY
    assert saved["startTime"] == "12:00"
    assert saved["endTime"] == "13:00"
    assert saved["mealType"] == "Lunch"
    assert saved["tables"] == [{"tableNumber": "T1", "seats": 4}, {"tableNumber": "T2", "seats": 2}]
    assert saved["message"]
    assert db.query(TableDAO).count() == 2


def test_slots_of_a_date_are_listed_as_the_pages_read_them(client, db):
    employee = login_as(db, "Employee")
    created = client.post("/api/slots", json=slot([("T1", 4), ("T2", 2)]), headers=employee).json()
    client.post("/api/slots", json=slot([("T1", 3)], day=OTHER_DAY), headers=employee)

    response = client.get(f"/api/slots?date={DAY}", headers=employee)

    assert response.status_code == 200
    assert response.history == []
    assert response.json() == [{
        "slotId": created["slotId"],
        "date": DAY,
        "startTime": "12:00",
        "endTime": "13:00",
        "mealType": None,
        "tables": [{"tableNumber": "T1", "seats": 4}, {"tableNumber": "T2", "seats": 2}],
    }]


def test_only_employee_and_warden_can_create_slots(client, db):
    hiker = login_as(db, "Hiker")
    warden = login_as(db, "Warden")

    assert client.post("/api/slots", json=slot([("T1", 4)])).status_code == 401
    assert client.post("/api/slots", json=slot([("T1", 4)]), headers=hiker).status_code == 403
    assert client.post("/api/slots", json=slot([("T1", 4)]), headers=warden).status_code == 201


def test_hiker_and_warden_can_list_the_slots(client, db):
    hiker = login_as(db, "Hiker")
    warden = login_as(db, "Warden")

    assert client.get(f"/api/slots?date={DAY}").status_code == 401
    assert client.get(f"/api/slots?date={DAY}", headers=hiker).status_code == 200
    assert client.get(f"/api/slots?date={DAY}", headers=warden).status_code == 200


def test_same_table_on_another_date_has_its_own_seats(client, db):
    employee = login_as(db, "Employee")
    client.post("/api/slots", json=slot([("T1", 6)]), headers=employee)

    response = client.post("/api/slots", json=slot([("T1", 8)], day=OTHER_DAY), headers=employee)

    assert response.status_code == 201
    assert db.query(TableDAO).count() == 1
    assert client.get(f"/api/slots?date={DAY}", headers=employee).json()[0]["tables"][0]["seats"] == 6
    assert client.get(f"/api/slots?date={OTHER_DAY}", headers=employee).json()[0]["tables"][0]["seats"] == 8


def test_saving_the_same_times_again_does_not_create_a_second_slot(client, db):
    employee = login_as(db, "Employee")
    first = client.post("/api/slots", json=slot([("T1", 4)], mealType="Lunch"), headers=employee).json()

    second = client.post("/api/slots", json=slot([("T2", 2)]), headers=employee).json()

    assert second["slotId"] == first["slotId"]
    assert db.query(TimeSlotDAO).count() == 1


def test_saving_a_table_again_changes_its_seats(client, db):
    employee = login_as(db, "Employee")
    client.post("/api/slots", json=slot([("T1", 4)]), headers=employee)

    client.post("/api/slots", json=slot([("T1", 6)]), headers=employee)

    assert client.get(f"/api/slots?date={DAY}", headers=employee).json()[0]["tables"] == [{"tableNumber": "T1", "seats": 6}]


def test_refused_request_leaves_nothing_behind(client, db):
    employee = login_as(db, "Employee")

    assert client.post("/api/slots", json=slot([("T1", 4), ("T2", 0)]), headers=employee).status_code == 422
    assert client.post("/api/slots", json=slot([("T1", 4)], start="14:00"), headers=employee).status_code == 409

    assert db.query(TimeSlotDAO).count() == 0
    assert db.query(TableDAO).count() == 0


def test_slot_without_tables_has_no_seats(client, db):
    employee = login_as(db, "Employee")

    created = client.post("/api/slots", json=slot([]), headers=employee).json()

    assert client.get(f"/api/slots/{created['slotId']}/availability").json()["total_capacity"] == 0


def test_hiker_books_a_slot_created_by_the_employee(client, db):
    employee = login_as(db, "Employee")
    hiker = login_as(db, "Hiker")
    client.post("/api/slots", json=slot([("T1", 8)]), headers=employee)
    listed = client.get(f"/api/slots?date={DAY}", headers=hiker).json()[0]

    booking = client.post("/api/reservations", json={
        "slot_id": listed["slotId"],
        "party_size": 8,
        "contact_name": "Anna Rossi",
        "contact_email": "anna@example.com",
    }, headers=hiker)

    assert booking.status_code == 201
    assert booking.history == []
    assert booking.json()["assigned_tables"][0]["table_number"] == "T1"
    assert client.get(f"/api/slots/{listed['slotId']}/availability").json()["remaining_seats"] == 0
