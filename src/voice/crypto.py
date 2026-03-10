"""Voice embedding encryption: Fernet (AES-128-CBC + HMAC-SHA256).

Encrypts embeddings at rest so a DB-only compromise yields only encrypted blobs.
The key lives in VOICE_ENCRYPTION_KEY env var, never in the database.

Backward compatibility: unencrypted (raw binary) embeddings are detected and
read transparently. New writes are always encrypted when a key is configured.
"""

from __future__ import annotations

import logging

from cryptography.fernet import Fernet, InvalidToken

from src.config import get_settings

logger = logging.getLogger(__name__)


def _get_fernet() -> Fernet | None:
    """Return a Fernet instance if VOICE_ENCRYPTION_KEY is configured."""
    key = get_settings().voice_encryption_key
    if not key:
        return None
    return Fernet(key.encode("utf-8"))


def encrypt_embedding(raw: bytes) -> bytes:
    """Encrypt serialized embedding bytes. Returns raw unchanged if no key configured."""
    f = _get_fernet()
    if f is None:
        return raw
    return f.encrypt(raw)


def decrypt_embedding(data: bytes) -> bytes:
    """Decrypt embedding bytes. Handles unencrypted legacy data transparently."""
    f = _get_fernet()
    if f is None:
        return data
    try:
        return f.decrypt(data)
    except InvalidToken:
        # Legacy unencrypted embedding — return as-is
        logger.debug("Embedding data is not Fernet-encrypted; treating as raw binary")
        return data
