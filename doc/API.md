# API List


All paths start with `/api` (the Vite dev server forwards them to the backend).<br>
Errors return `{"detail": "message"}`. Live docs: http://localhost:8000/docs

## GET

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
  "detail": "Time slot with id 1 not found."
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
  "detail": "Reservation with reference 'MH-20261030-ALX01' not found."
}
```

**preview booking confirmation email**

name: `/api/reservations/{reference}/email-preview`<br>
parameter: `reference` (path, string)<br>
HTTP Status: 200 ok, 404 not found, 500 ISE<br>
JSON response:
```json
// 200
{
  "booking_reference": "MH-20261030-ALX01",
  "recipient_email": "hiker1@example.com",
  "subject": "Mountain Hut Booking Confirmation [MH-20261030-ALX01]",
  "email_text": "...",
  "email_html": "..."
}

// 404
{
  "detail": "Reservation with reference 'MH-20261030-ALX01' not found."
}
```

**get hiker reservations**

name: `/api/reservations/user/{user_id}`<br>
parameter: `user_id` (path, integer)<br>
HTTP Status: 200 ok, 500 ISE<br>
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
HTTP Status: 201 ok, 500 ISE,404 Not Found (unknown service) <br>
JSON response: 
```json 
//201
{
  "userId": 101,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "role": "Hiker",
  "message": "Registration successful"
}

//404
{
    "detail":string
}

//500
{
    "detail":string
}
```
**login**

name: `/api/counters/{id_counter}/next-customer`<br>
parameter: -<br>
body:
```json
{
  "username": "manager@mountainhut.com",
  "password": "SecurePassword123!"
}
```
HTTP Status: 200 ok, 204 no content, 404 not found, 500 ISE <br>
JSON responses: 
```json
//200 
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "email": "manager@mountainhut.com",
    "firstName": "Firstname",
    "lastName": "Lastname",
    "role": "Manager"  // "Hiker" | "Employee" | "Manager"
  }
}
//404
{
    "detail": string
}
//500
{
    "detail":string
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
HTTP Status: 201 ok, 400 bad request, 404 not found, 500 ISE<br>
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

// 400 / 404 / 500
{
  "detail": "message"
}
```

## PUT


## DELETE
