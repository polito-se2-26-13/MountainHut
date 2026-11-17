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

**get slot availability (MH-04)**

name: `/api/slots/{slot_id}/availability`<br>
parameters:
- `slot_id` (path, integer, required)
- `party_size` or `partySize` (query, integer >= 1, optional) — evaluates real-time table layout allocation for the party<br>
authentication: public (no login required)<br>
HTTP Status: 200 ok, 404 not found, 500 ISE<br>
JSON response:
```json
// 200 without party_size
{
  "slot_id": 1,
  "date": "2026-10-30",
  "start_time": "12:00",
  "end_time": "13:00",
  "meal_type": "Lunch",
  "status": "OPEN",
  "total_capacity": 34,
  "reserved_seats": 6,
  "remaining_seats": 28,
  "is_available": true,
  "party_size": null,
  "layout_summary": null,
  "layout": null,
  "tables": [
    {
      "table_number": "T1",
      "capacity": 6,
      "occupied_seats": 6,
      "free_seats": 0,
      "location": "Indoor Main Hall"
    },
    {
      "table_number": "T2",
      "capacity": 4,
      "occupied_seats": 0,
      "free_seats": 4,
      "location": "Indoor Main Hall"
    }
  ]
}

// 200 with party_size=6 (e.g. split party layout: 3 + 2 + 1 seats)
{
  "slot_id": 6,
  "date": "2026-11-24",
  "start_time": "13:00",
  "end_time": "14:00",
  "meal_type": "Lunch",
  "status": "OPEN",
  "total_capacity": 12,
  "reserved_seats": 6,
  "remaining_seats": 6,
  "is_available": true,
  "party_size": 6,
  "layout_summary": "3 + 2 + 1 seats",
  "layout": [
    { "table_number": "T11", "assigned_seats": 3, "location": "Main Dining Hall" },
    { "table_number": "T10", "assigned_seats": 2, "location": "Main Dining Hall" },
    { "table_number": "T12", "assigned_seats": 1, "location": "Stube Cozy Corner" }
  ],
  "tables": [
    { "table_number": "T10", "capacity": 6, "occupied_seats": 4, "free_seats": 2, "location": "Main Dining Hall" },
    { "table_number": "T11", "capacity": 4, "occupied_seats": 1, "free_seats": 3, "location": "Main Dining Hall" },
    { "table_number": "T12", "capacity": 2, "occupied_seats": 1, "free_seats": 1, "location": "Stube Cozy Corner" }
  ]
}

// 404
{
  "code": 404,
  "message": "Time slot with id 1 not found.",
  "name": "NotFoundError"
}
```

**check availability by date and time (MH-04)**

name: `/api/slots/availability`<br>
parameters:
- `date` (query, date string `YYYY-MM-DD`, required)
- `time` (query, time string `HH:MM`, required)
- `party_size` or `partySize` (query, integer >= 1, optional)<br>
authentication: public (no login required)<br>
HTTP Status: 200 ok, 404 not found, 500 ISE<br>
JSON response: identical to `/api/slots/{slot_id}/availability`
```

**get reservation by reference**

name: `/api/reservations/{reference}`<br>
parameter: `reference` (path, string)<br>
header: `Authorization: Bearer <token>` (Hiker, Employee or Warden), a hiker can read only their own bookings<br>
HTTP Status: 200 ok, 401 unauthorized, 403 forbidden, 404 not found, 500 ISE<br>
JSON response:
```json
// 200
{
  "id": 1,
  "booking_reference": "MH-20261030-ALX01",
  "user_id": 3,
  "slot_id": 1,
  "date": "2026-10-30",
  "start_time": "12:00",
  "end_time": "13:00",
  "party_size": 4,
  "special_requirements": [
    {"has_allergy": false, "description": "2 vegetarian meals"},
    {"has_allergy": true, "description": "1 gluten allergy"}
  ],
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
header: `Authorization: Bearer <token>` (Hiker), only for the id of the hiker of the token<br>
HTTP Status: 200 ok, an empty list when there are no bookings, 401 unauthorized, 403 forbidden, 422 id not a number, 500 ISE<br>
JSON response:
```json
// 200
[
  {
    "id": 1,
    "booking_reference": "MH-20261030-ALX01",
    "user_id": 3,
    "slot_id": 1,
    "date": "2026-10-30",
    "start_time": "12:00",
    "end_time": "13:00",
    "party_size": 4,
    "special_requirements": [
      {"has_allergy": false, "description": "2 vegetarian meals"},
      {"has_allergy": true, "description": "1 gluten allergy"}
    ],
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
  "notes": "registered mountain guide",
  "emergencyContact": "Marco Rossi, +39 333 7654321",
  "role": "Hiker"
}
```
`role` can be left out and is ignored: the registration always creates a Hiker. The password needs at least 8 characters, and the email is saved in lowercase. `phone` is required, and a number without prefix is read as Italian. `notes` and `emergencyContact` are optional, at most 555 and 255 characters. Names are saved without the spaces around them, so a name of only spaces is refused.<br>
HTTP Status: 201 ok, 409 email already registered, 422 missing or invalid fields, 500 ISE<br>
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
HTTP Status: 200 ok, 400 empty field, 401 wrong email or password, 422 missing field, 500 ISE<br>
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

// 401 / 500
{
  "code": 401,
  "message": "email or password wrong",
  "name": "UnauthorizedError"
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
Saving the same date and times again adds or updates only the listed tables, while the meal and the other tables stay as they are. A table number used for the first time creates the table. A table cannot get fewer seats than the ones already booked on it.<br>
A new slot cannot overlap another slot of the same day, while one right after another is fine. Every table needs a name of 1 to 50 characters, written once.<br>
HTTP Status: 201 created, 401 unauthorized, 403 forbidden, 409 overlaps another slot of the same day or fewer seats than the booked ones, 422 invalid request, start time not before end time, slot in the past or invalid table name, 500 ISE<br>
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
header: `Authorization: Bearer <token>` (Hiker)<br>
body, where `user_id` can be left out because the hiker comes from the token:
```json
{
  "slot_id": 1,
  "party_size": 4,
  "user_id": 3,
  "contact_name": "Alex Smith",
  "contact_email": "hiker1@example.com",
  "contact_phone": "+39 340 1234567",
  "special_requirements": [
    {"has_allergy": false, "description": "2 vegetarian meals"},
    {"has_allergy": true, "description": "1 gluten allergy"}
  ]
}
```
HTTP Status: 201 created, 401 unauthorized, 403 forbidden, 404 slot not found, 409 slot closed, too late, already booked or not enough seats, 422 invalid request, 500 ISE<br>
JSON response:
```json
// 201
{
  "id": 1,
  "booking_reference": "MH-20261030-ALX01",
  "user_id": 3,
  "slot_id": 1,
  "date": "2026-10-30",
  "start_time": "12:00",
  "end_time": "13:00",
  "party_size": 4,
  "special_requirements": [
    {"has_allergy": false, "description": "2 vegetarian meals"},
    {"has_allergy": true, "description": "1 gluten allergy"}
  ],
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

**change reservation**

name: `/api/reservations/reference/{reference}/change`<br>
parameter: `reference` booking reference<br>
header: `Authorization: Bearer <token>` (Hiker, owner of the booking)<br>
body, the whole booking again; the list replaces the old requirements and an empty list removes them:
```json
{
  "slot_id": 2,
  "party_size": 5,
  "special_requirements": [
    {"has_allergy": true, "description": "1 gluten allergy"}
  ]
}
```
The change is treated as a new booking (MH-06): it is allowed until 48 hours before the old slot and before the new one, the seats are given back and the tables assigned again, and the confirmation is sent again by email.<br>
HTTP Status: 200 ok, 401 unauthorized, 403 not the owner, 404 booking or slot not found, 409 not confirmed, too late, slot closed, already booked in that slot or not enough seats (the booking stays as it was), 422 invalid request, 500 ISE<br>
JSON response: the booking as in **create reservation**, with code 200.

## DELETE
