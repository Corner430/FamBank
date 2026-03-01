"""JWT auth module: encode/decode tokens for phone+SMS authentication.

Replaces the old PIN-based auth. JWT claims include user_id, family_id (nullable),
and role (nullable). Access token expires in 24h, refresh token in 30d.
"""

import hashlib
import os
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

_secret = os.getenv("JWT_SECRET_KEY", "")
if not _secret:
    import warnings

    _secret = "fambank-dev-only-change-in-production"
    warnings.warn(
        "JWT_SECRET_KEY is not set! Using insecure default. "
        "Set JWT_SECRET_KEY env var before deploying to production.",
        stacklevel=1,
    )

SECRET_KEY: str = _secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24
REFRESH_TOKEN_EXPIRE_DAYS = 30


def create_access_token(
    user_id: int,
    family_id: int | None = None,
    role: str | None = None,
) -> str:
    """Create a JWT access token with user_id, family_id, and role claims."""
    expire = datetime.now(UTC) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = {
        "sub": str(user_id),
        "family_id": family_id,
        "role": role,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Create a JWT refresh token (longer-lived, minimal claims)."""
    expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def hash_token(token: str) -> str:
    """Hash a refresh token for DB storage using SHA-256."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
