"""Authentication: password hashing (stdlib PBKDF2) and session cookies.

No third-party auth library. Sessions are random tokens; only the SHA-256
hash of a token is stored in the database, and the cookie is HttpOnly.
"""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta

from .db import connect

SESSION_DAYS = 30
_PBKDF2_ITERATIONS = 200_000


def hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    ).hex()


def new_salt() -> bytes:
    return os.urandom(16)


def verify_password(password: str, salt_hex: str, expected_hash: str) -> bool:
    if not salt_hex or not expected_hash:
        return False
    salt = bytes.fromhex(salt_hex)
    return hmac.compare_digest(hash_password(password, salt), expected_hash)


def create_session(user_id: int) -> str:
    """Create a session, return the raw token to put in the cookie."""
    token = secrets.token_hex(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires = (datetime.utcnow() + timedelta(days=SESSION_DAYS)).isoformat()
    conn = connect()
    try:
        conn.execute(
            "INSERT INTO sessions (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
            (user_id, token_hash, expires),
        )
        conn.commit()
    finally:
        conn.close()
    return token


def get_user_from_token(token: str | None):
    """Return the user row for a session token, or None."""
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = connect()
    try:
        row = conn.execute(
            """
            SELECT u.* FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > datetime('now')
            """,
            (token_hash,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def destroy_session(token: str | None) -> None:
    if not token:
        return
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = connect()
    try:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
        conn.commit()
    finally:
        conn.close()
