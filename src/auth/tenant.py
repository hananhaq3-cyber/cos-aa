"""
Tenant validation, quota checking, and API key encryption/decryption.
Uses AES-256-GCM for authenticated encryption with key versioning.
"""
import base64
import hashlib
import os
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from src.core.config import settings
from src.core.exceptions import QuotaExceededError
from src.db.redis_client import redis_client, RedisClient

NONCE_SIZE = 12  # 96-bit nonce for GCM
VERSION_BYTE_SIZE = 1


def _derive_key(version: int | None = None) -> bytes:
    """Derive a 256-bit key from app_secret_key + version."""
    v = version if version is not None else settings.encryption_key_version
    raw = f"{settings.app_secret_key}:v{v}".encode()
    return hashlib.sha256(raw).digest()  # 32 bytes = AES-256


def encrypt_api_key(plaintext: str, version: int | None = None) -> str:
    """
    Encrypt with AES-256-GCM.
    Output format: base64(version_byte || 12-byte_nonce || ciphertext || 16-byte_GCM_tag)
    """
    v = version if version is not None else settings.encryption_key_version
    key = _derive_key(v)
    aesgcm = AESGCM(key)
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    # Pack: version (1 byte) + nonce (12 bytes) + ciphertext+tag
    packed = bytes([v]) + nonce + ciphertext
    return base64.urlsafe_b64encode(packed).decode()


def decrypt_api_key(ciphertext_b64: str) -> str:
    """
    Decrypt AES-256-GCM payload.
    Extracts version byte to derive the correct key (supports key rotation).
    """
    packed = base64.urlsafe_b64decode(ciphertext_b64.encode())
    version = packed[0]
    nonce = packed[VERSION_BYTE_SIZE : VERSION_BYTE_SIZE + NONCE_SIZE]
    ciphertext = packed[VERSION_BYTE_SIZE + NONCE_SIZE :]
    key = _derive_key(version)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode()


async def check_quota(
    tenant_id: UUID, resource: str, increment: int = 1
) -> None:
    key = RedisClient.rate_limit_key(tenant_id, f"quota:{resource}")
    client = redis_client.client
    current = await client.incrby(key, increment)

    ttl = await client.ttl(key)
    if ttl == -1:
        await client.expire(key, 86400)

    limits = {
        "llm_tokens": 5_000_000,
        "sessions": 1000,
        "agent_spawns": 20,
        "concurrent_tasks": 50,
    }
    limit = limits.get(resource, 10000)

    if current > limit:
        raise QuotaExceededError(resource, str(tenant_id))
