"""
Password hashing and verification using bcrypt via passlib.
"""
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bcrypt has a 72-byte limit for passwords
MAX_PASSWORD_LENGTH = 72


def hash_password(plain: str) -> str:
    """Hash password with bcrypt (truncates to 72 bytes if needed)."""
    # Bcrypt only supports up to 72 bytes
    truncated = plain[:MAX_PASSWORD_LENGTH]
    return _pwd_context.hash(truncated)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against hash (truncates to 72 bytes if needed)."""
    # Bcrypt only supports up to 72 bytes
    truncated = plain[:MAX_PASSWORD_LENGTH]
    return _pwd_context.verify(truncated, hashed)

