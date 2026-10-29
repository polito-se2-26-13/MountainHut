# API List


All paths start with `/api` (the Vite dev server forwards them to the backend).<br>
Errors return `{"detail": "message"}`. Live docs: http://localhost:8000/docs

## GET

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
## PUT


## DELETE