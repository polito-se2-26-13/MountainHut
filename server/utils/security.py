"""Security and password hashing utilities using standard library."""
import hashlib
import os
import secrets


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2 HMAC SHA-256 with random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations=100000,
    )
    return f"{salt}${key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    """Verify a plain password against the stored salt$hash string."""
    try:
        salt, stored_hash = hashed.split("$", 1)
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations=100000,
        )
        return secrets.compare_digest(key.hex(), stored_hash)
    except Exception:
        return False

