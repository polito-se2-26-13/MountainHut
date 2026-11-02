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
URL_SERVICE = "services"
URL_TICKET  = "tickets"

ROUTES = {
    "AUTH": BASEURL + URL_AUTH,
    "SERVICE": BASEURL + URL_SERVICE,
    "TICKET":  BASEURL + URL_TICKET,
}

# JWT Configuration
TOKEN_LIFESPAN_HOURS = 24
SECRET_KEY = "b}2ZzqQ!eQ!t7rFeT[GHs6FZ+*L]2VqR{vnLn>4-V3[5W-V{fk"
ALGORITHM = "HS256"