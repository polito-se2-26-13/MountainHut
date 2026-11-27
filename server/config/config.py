import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASEURL = "/api/"
    #f"sqlite:///{Path(__file__).parent / 'mountainHut.sqlite'}"
ORIGIN = [
    "http://localhost:3000",
    "http://localhost:5173",
]
# route keys
URL_AUTH = "auth"
URL_RESERVATION = "reservations"
URL_SLOT  = "slots"
URL_USER="users"

ROUTES = {
    "AUTH": BASEURL + URL_AUTH,
    "RESERVATION": BASEURL + URL_RESERVATION,
    "SLOT":  BASEURL + URL_SLOT,
    "USER":BASEURL+URL_USER,
}

# JWT Configuration
TOKEN_LIFESPAN_HOURS = 24
# from server/.env and never in the code, since anyone who knows it can sign a login for any account;
# without it a random key is made at every start, so the logins end when the server restarts
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
ALGORITHM = "HS256"