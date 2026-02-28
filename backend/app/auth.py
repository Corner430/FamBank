"""PIN/password auth service with bcrypt hashing and session tokens."""

from datetime import UTC, datetime, timedelta

import bcrypt
from jose import jwt

SECRET_KEY = "fambank-secret-key-change-in-production"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24


def hash_pin(pin: str) -> str:
    """Hash a PIN/password with bcrypt."""
    return bcrypt.hashpw(pin.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    """Verify a PIN/password against its hash."""
    return bcrypt.checkpw(plain_pin.encode("utf-8"), hashed_pin.encode("utf-8"))


def create_token(user_id: int, role: str) -> str:
    """Create a JWT session token."""
    expire = datetime.now(UTC) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception:
        return None
