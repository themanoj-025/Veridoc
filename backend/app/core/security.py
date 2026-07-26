"""Security utilities — password hashing, JWT tokens, file encryption."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password Hashing ─────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT Tokens ───────────────────────────────────────────

def _create_token(data: dict, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    to_encode.update({
        "exp": datetime.now(timezone.utc) + expires_delta,
        "iat": datetime.now(timezone.utc),
    })
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(user_id: uuid.UUID) -> str:
    """Create a short-lived JWT access token."""
    return _create_token(
        {"sub": str(user_id), "type": "access"},
        timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(user_id: uuid.UUID) -> str:
    """Create a longer-lived JWT refresh token."""
    return _create_token(
        {"sub": str(user_id), "type": "refresh"},
        timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


# ── File Encryption (at rest) ────────────────────────────

def _get_fernet() -> Fernet:
    """Get a Fernet instance from the encryption key."""
    key = settings.file_encryption_key
    # Pad or truncate to 32 bytes then base64-encode
    if len(key) != 44:  # not already base64-encoded valid key
        import base64
        import hashlib
        key_bytes = hashlib.sha256(key.encode()).digest()
        key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(key)


def encrypt_file(data: bytes) -> tuple[bytes, str]:
    """Encrypt file bytes. Returns (encrypted_data, iv_hex)."""
    f = _get_fernet()
    encrypted = f.encrypt(data)
    # Extract IV from the Fernet token (first part after base64 decode)
    import base64
    decoded = base64.urlsafe_b64decode(encrypted)
    iv = decoded[:16].hex()
    return encrypted, iv


def decrypt_file(encrypted_data: bytes) -> bytes:
    """Decrypt file bytes."""
    f = _get_fernet()
    return f.decrypt(encrypted_data)
