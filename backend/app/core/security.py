"""Password hashing, JWT, and field-level encryption."""
import base64
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import jwt
import os

from app.core.config import get_settings
from app.models.base import utcnow

settings = get_settings()
_ph = PasswordHasher()


# ---- passwords ----
def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except VerifyMismatchError:
        return False


# ---- JWT ----
def create_access_token(subject: str, extra: dict | None = None) -> str:
    now = utcnow()
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


# ---- field-level encryption (SSN / EIN / direct deposit) ----
def _key() -> bytes:
    raw = base64.b64decode(settings.field_encryption_key)
    # Normalize to 32 bytes for AES-256.
    return (raw + b"\0" * 32)[:32]


def encrypt_field(plaintext: str | None) -> str | None:
    if plaintext is None or plaintext == "":
        return plaintext
    nonce = os.urandom(12)
    ct = AESGCM(_key()).encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ct).decode()


def decrypt_field(token: str | None) -> str | None:
    if token is None or token == "":
        return token
    blob = base64.b64decode(token)
    nonce, ct = blob[:12], blob[12:]
    return AESGCM(_key()).decrypt(nonce, ct, None).decode()


def mask_tail(value: str | None, keep: int = 4) -> str | None:
    """Mask all but the last `keep` characters, e.g. '•••-••-1234'."""
    if not value:
        return value
    tail = value[-keep:]
    return "•" * max(0, len(value) - keep) + tail
