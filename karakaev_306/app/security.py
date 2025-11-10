from __future__ import annotations

import hashlib
import hmac
import os
from typing import Tuple


PBKDF2_ITERATIONS = 200_000
SALT_LENGTH = 16


def hash_password(password: str) -> str:
    """Return PBKDF2 hash in the format iterations$salt_hex$hash_hex."""
    if not password:
        raise ValueError("Password must not be empty.")
    salt = os.urandom(SALT_LENGTH)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def _split_hash(stored_hash: str) -> Tuple[int, bytes, bytes]:
    parts = stored_hash.split("$")
    if len(parts) != 3:
        raise ValueError("Unsupported password hash format.")
    iterations = int(parts[0])
    salt = bytes.fromhex(parts[1])
    hash_bytes = bytes.fromhex(parts[2])
    return iterations, salt, hash_bytes


def verify_password(password: str, stored_hash: str) -> bool:
    """Validate a password against a stored hash."""
    try:
        iterations, salt, expected = _split_hash(stored_hash)
    except (ValueError, TypeError):
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)

