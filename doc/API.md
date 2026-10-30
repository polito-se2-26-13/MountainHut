# API List

All paths start with `/api` (the Vite dev server forwards them to the backend).<br>
Errors return `{"detail": "message"}`. Live docs: http://localhost:8000/docs

## GET

**get slots for copy**

name: `/api/slots?date={date}`<br>
parameter: `date` (required, query, `YYYY-MM-DD`) — date whose existing service slots should be returned.<br>
header: `Authorization: Bearer <token>` (Employee access)<br>

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
HTTP Status: 201 ok, 500 ISE, 404 Not Found (unknown service)<br>
JSON response:
```json
// 201
{
  "userId": 101,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "role": "Hiker",
  "message": "Registration successful"
}

// 404 / 500
{
  "detail": "message"
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
HTTP Status: 200 ok, 404 not found, 500 ISE<br>
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
    "role": "Manager"  // "Hiker" | "Employee" | "Manager"
  }
}

// 404 / 500
{
  "detail": "message"
}
```

**create service slot**

name: `/api/slots`<br>
parameter: -<br>
header: `Authorization: Bearer <token>` (Employee access)<br>
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
HTTP Status: 201 created, 401 unauthorized, 403 forbidden, 404 Not Found (unknown service), 422 invalid request, 500 ISE<br>
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

// Error response
{
  "detail": "message"
}
```

## PUT

## DELETE
