"""
Password hashing and verification using bcrypt via passlib.
"""
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash password with bcrypt."""
    # Password length is validated in auth_schemas.py (max 72 bytes for bcrypt)
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against hash."""
    # Password length is validated in auth_schemas.py (max 72 bytes for bcrypt)
    return _pwd_context.verify(plain, hashed)


