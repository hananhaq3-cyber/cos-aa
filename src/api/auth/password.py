"""
Password hashing and verification using Argon2 via passlib.
"""
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash password with Argon2 (more secure than bcrypt, no byte limit)."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against hash."""
    return _pwd_context.verify(plain, hashed)



