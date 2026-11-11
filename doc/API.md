# API List

All paths start with `/api` (the Vite dev server forwards them to the backend).<br>
Errors return `{"code": 409, "message": "message", "name": "ConflictError"}`. Invalid requests and token errors return `{"detail": ...}` instead. Live docs: http://localhost:8000/docs

## GET

**get slots for copy**

name: `/api/slots?date={date}`<br>
parameter: `date` (query, `YYYY-MM-DD`) — date whose existing service slots should be returned. Without it, all slots are returned.<br>
header: `Authorization: Bearer <token>` (Hiker, Employee or Warden)<br>

HTTP Status: 200 ok, 401 unauthorized, 403 forbidden, 422 invalid date, 500 ISE<br>
JSON response:
```json
[
  {
    "slotId": 101,
    "date": "2026-10-28",
    "startTime": "12:00",
    "endTime": "13:00",
    "mealType": "Lunch",
    "tables": [
      { "tableNumber": "T1", "seats": 4 },
      { "tableNumber": "T2", "seats": 2 }
    ]
  },
  {
    "slotId": 102,
    "date": "2026-10-28",
    "startTime": "19:00",
    "endTime": "20:30",
    "mealType": "Dinner",
    "tables": [
      { "tableNumber": "T1", "seats": 4 },
      { "tableNumber": "T2", "seats": 4 },
      { "tableNumber": "T3", "seats": 2 }
    ]
  }
]
```

If there are no slots for the date, return an empty array: `[]`.<br>
Error response:
```json
{
  "detail": "message"
}
```

**get slot availability**

name: `/api/slots/{slot_id}/availability`<br>
parameter: `slot_id` (path, integer)<br>
HTTP Status: 200 ok, 404 not found, 500 ISE<br>
JSON response:
```json
// 200
{
  "slot_id": 1,
  "date": "2026-10-30",
  "start_time": "12:00",
  "end_time": "13:00",
  "meal_type": "Lunch",
  "status": "OPEN",
  "total_capacity": 34,
  "reserved_seats": 6,
  "remaining_seats": 28
}

// 404
{
  "code": 404,
  "message": "Time slot with id 1 not found.",
  "name": "NotFoundError"
}
```

**get reservation by reference**

name: `/api/reservations/{reference}`<br>
parameter: `reference` (path, string)<br>
HTTP Status: 200 ok, 404 not found, 500 ISE<br>
JSON response:
```json
// 200
{
  "id": 1,
  "booking_reference": "MH-20261030-ALX01",
  "user_id": 3,
  "slot_id": 1,
  "party_size": 4,
  "special_requirements": "2 vegetarian meals, 1 gluten allergy",
  "contact_name": "Alex Smith",
  "contact_email": "hiker1@example.com",
  "contact_phone": "+39 340 1234567",
  "status": "CONFIRMED",
  "assigned_tables": [
    {
      "table_id": 1,
      "table_number": "T1",
      "location": "Indoor Main Hall",
      "assigned_seats": 4
    }
  ],
  "created_at": "2026-10-30T12:00:00"
}

// 404
{
  "code": 404,
  "message": "booking reference not found",
  "name": "NotFoundError"
}
```

**get hiker reservations**

name: `/api/reservations/user/{user_id}`<br>
parameter: `user_id` (path, integer)<br>
HTTP Status: 200 ok, 404 no bookings, 500 ISE<br>
JSON response:
```json
// 200
[
  {
    "id": 1,
    "booking_reference": "MH-20261030-ALX01",
    "user_id": 3,
    "slot_id": 1,
    "party_size": 4,
    "special_requirements": "2 vegetarian meals, 1 gluten allergy",
    "contact_name": "Alex Smith",
    "contact_email": "hiker1@example.com",
    "contact_phone": "+39 340 1234567",
    "status": "CONFIRMED",
    "assigned_tables": [
      {
        "table_id": 1,
        "table_number": "T1",
        "location": "Indoor Main Hall",
        "assigned_seats": 4
      }
    ],
    "created_at": "2026-10-30T12:00:00"
  }
]
```

## POST

**registration**

name: `/api/auth/register`<br>
parameter:-<br>
body:
```json
{
  "email": "hiker@example.com",
  "password": "SecurePassword123!",
  "firstName": "Firstname",
  "lastName": "Lastname",
  "phone": "+39 333 1234567",
  "role": "Hiker"
}
```
HTTP Status: 201 ok, 400 empty field, 409 email already registered, 422 invalid fields, 500 ISE<br>
JSON response:
```json
// 201
{
  "id": 101
}

// 409 / 500
{
  "code": 409,
  "message": "message",
  "name": "ConflictError"
}
```

**login**

name: `/api/auth/login`<br>
parameter: -<br>
body:
```json
{
  "username": "manager@mountainhut.com",
  "password": "SecurePassword123!"
}
```
HTTP Status: 200 ok, 400 empty field, 404 wrong email or password, 422 missing field, 500 ISE<br>
JSON response:
```json
// 200
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "email": "manager@mountainhut.com",
    "firstName": "Firstname",
    "lastName": "Lastname",
    "role": "Manager",  // "Hiker" | "Employee" | "Manager" | "Warden"
    "phone": "+393331234567"
  }
}

// 404 / 500
{
  "code": 404,
  "message": "email or password wrong",
  "name": "NotFoundError"
}
```

**create service slot**

name: `/api/slots`<br>
parameter: -<br>
header: `Authorization: Bearer <token>` (Employee or Warden)<br>
body:
```json
{
  "date": "2026-11-01",
  "startTime": "12:00",
  "endTime": "13:00",
  "mealType": "Lunch",
  "tables": [
    { "tableNumber": "T1", "seats": 4 },
    { "tableNumber": "T2", "seats": 2 },
    { "tableNumber": "T3", "seats": 6 }
  ]
}
```
`mealType` is optional. Suggested values: `Lunch`, `Dinner`, `Snack`.<br>
Saving the same date and times again adds or updates only the listed tables, while the meal and the other tables stay as they are. A table number used for the first time creates the table.<br>
A new slot cannot overlap another slot of the same day, while one right after another is fine. Every table needs a name of 1 to 50 characters, written once.<br>
HTTP Status: 201 created, 401 unauthorized, 403 forbidden, 409 overlaps another slot of the same day, 422 invalid request, start time not before end time, slot in the past or invalid table name, 500 ISE<br>
JSON response:
```json
// 201
{
  "slotId": 103,
  "date": "2026-11-01",
  "startTime": "12:00",
  "endTime": "13:00",
  "mealType": "Lunch",
  "tables": [
    { "tableNumber": "T1", "seats": 4 },
    { "tableNumber": "T2", "seats": 2 },
    { "tableNumber": "T3", "seats": 6 }
  ],
  "message": "Slot created successfully"
}
```

**create reservation**

name: `/api/reservations`<br>
parameter: -<br>
body:
```json
{
  "slot_id": 1,
  "party_size": 4,
  "user_id": 3,
  "contact_name": "Alex Smith",
  "contact_email": "hiker1@example.com",
  "contact_phone": "+39 340 1234567",
  "special_requirements": "2 vegetarian meals, 1 gluten allergy"
}
```
HTTP Status: 201 created, 404 slot not found, 409 slot closed, too late, already booked or not enough seats, 422 invalid request, 500 ISE<br>
JSON response:
```json
// 201
{
  "id": 1,
  "booking_reference": "MH-20261030-ALX01",
  "user_id": 3,
  "slot_id": 1,
  "party_size": 4,
  "special_requirements": "2 vegetarian meals, 1 gluten allergy",
  "contact_name": "Alex Smith",
  "contact_email": "hiker1@example.com",
  "contact_phone": "+39 340 1234567",
  "status": "CONFIRMED",
  "assigned_tables": [
    {
      "table_id": 1,
      "table_number": "T1",
      "location": "Indoor Main Hall",
      "assigned_seats": 4
    }
  ],
  "created_at": "2026-10-30T12:00:00"
}

// 404 / 409 / 500
{
  "code": 409,
  "message": "message",
  "name": "ConflictError"
}
```

## PUT

## DELETE
