"""
security.py — passwords + JWT access tokens.  (PROTOTYPE: no refresh-token flow)
"""

from datetime import datetime, timedelta, timezone
from functools import wraps
import uuid

import bcrypt
from flask import current_app
from flask_jwt_extended import (
    create_access_token,
    decode_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)

from app.core.errors import APIError
from app.extensions import db
from app.models.user import User

BCRYPT_ROUNDS = 12
_DUMMY_HASH = bcrypt.hashpw(b"pramaan-dummy-password", bcrypt.gensalt(rounds=BCRYPT_ROUNDS))


def hash_password(plaintext: str) -> str:
    raw = plaintext.encode("utf-8")
    if len(raw) > 72:
        raise ValueError("Password must be at most 72 bytes")
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode("ascii")


def verify_password(plaintext: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plaintext.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def verify_password_dummy(plaintext: str) -> None:
    """Run bcrypt against a dummy hash so unknown emails take similar time."""
    bcrypt.checkpw(plaintext.encode("utf-8")[:72], _DUMMY_HASH)


def _ttl() -> timedelta:
    return timedelta(seconds=int(current_app.config.get("JWT_ACCESS_TTL_SECONDS", 28800)))


def issue_access_token(user: User, *, mfa_at: int | None = None) -> str:
    if mfa_at is None:
        mfa_at = int(datetime.now(timezone.utc).timestamp())
    return create_access_token(
        identity=str(user.id),
        expires_delta=_ttl(),
        additional_claims={
            "role": user.role,
            "dept": str(user.department_id),
            "mfa_at": mfa_at,
        },
    )


def issue_temp_mfa_token(user: User) -> str:
    return create_access_token(
        identity=str(user.id),
        expires_delta=timedelta(minutes=5),
        additional_claims={"purpose": "mfa", "role": user.role, "dept": str(user.department_id)},
    )


def decode_temp_mfa_token(temp_token: str) -> User:
    try:
        decoded = decode_token(temp_token)
    except Exception as exc:
        raise APIError(401, "UNAUTHORIZED", "Invalid or expired MFA token") from exc
    if decoded.get("purpose") != "mfa":
        raise APIError(401, "UNAUTHORIZED", "Invalid or expired MFA token")
    user = load_user_by_id(decoded["sub"])
    if not user or not user.is_active:
        raise APIError(401, "UNAUTHORIZED", "Invalid or expired MFA token")
    return user


def load_user_by_id(user_id: str | None) -> User | None:
    if not user_id:
        return None
    try:
        uid = uuid.UUID(str(user_id))
    except ValueError:
        return None
    return db.session.get(User, uid)


def current_user_required() -> User:
    user = load_user_by_id(get_jwt_identity())
    if not user or not user.is_active:
        raise APIError(401, "UNAUTHORIZED", "unauthorised")
    return user


def require_access_jwt(fn):
    """Reject MFA temp tokens (`purpose=mfa`). Use on all non-verify routes."""

    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if get_jwt().get("purpose") == "mfa":
            raise APIError(401, "UNAUTHORIZED", "MFA verification required")
        return fn(*args, **kwargs)

    return wrapper
