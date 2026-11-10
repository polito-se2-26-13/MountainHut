from pathlib import Path

BASEURL = "/api/"
DATABASE_URL="sqlite+aiosqlite:///mountainHut.sqlite"
    #f"sqlite:///{Path(__file__).parent / 'mountainHut.sqlite'}"
ORIGIN = [
    "http://localhost:3000",
    "http://localhost:5173",
]
# route keys
URL_AUTH = "auth"
URL_RESERVATION = "reservations"
URL_SLOT  = "slots"

ROUTES = {
    "AUTH": BASEURL + URL_AUTH,
    "RESERVATION": BASEURL + URL_RESERVATION,
    "SLOT":  BASEURL + URL_SLOT,
}

# JWT Configuration
TOKEN_LIFESPAN_HOURS = 24
SECRET_KEY = "b}2ZzqQ!eQ!t7rFeT[GHs6FZ+*L]2VqR{vnLn>4-V3[5W-V{fk"
ALGORITHM = "HS256"