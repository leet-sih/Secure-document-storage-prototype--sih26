"""
auth_service.py — login, MFA, and session issuance logic.
"""

from datetime import datetime, timedelta, timezone

from flask import current_app
from sqlalchemy import func

from app.core.errors import APIError
from app.core.security import (
    decode_temp_mfa_token,
    issue_access_token,
    issue_temp_mfa_token,
    verify_password,
    verify_password_dummy,
)
from app.core import totp
from app.extensions import db
from app.models.user import User


def authenticate(email: str, password: str) -> User:
    now = datetime.now(timezone.utc)
    user = User.query.filter(func.lower(User.email) == email.lower()).one_or_none()
    if user is None:
        verify_password_dummy(password)
        raise APIError(401, "UNAUTHORIZED", "Invalid credentials")

    if not user.is_active:
        raise APIError(403, "FORBIDDEN", "Account is deactivated")

    if user.locked_until is not None and user.locked_until > now:
        raise APIError(423, "LOCKED", "Account locked after repeated failed attempts")

    if not verify_password(password, user.password_hash):
        user.failed_logins = (user.failed_logins or 0) + 1
        threshold = int(current_app.config.get("ACCOUNT_LOCKOUT_THRESHOLD", 5))
        minutes = int(current_app.config.get("ACCOUNT_LOCKOUT_MINUTES", 15))
        locked = user.failed_logins >= threshold
        if locked:
            user.locked_until = now + timedelta(minutes=minutes)
        db.session.commit()
        raise APIError(401, "UNAUTHORIZED", "Invalid credentials")

    user.failed_logins = 0
    user.locked_until = None
    db.session.commit()
    return user


def begin_session(user: User) -> dict:
    ttl = int(current_app.config.get("JWT_ACCESS_TTL_SECONDS", 28800))
    if user.totp_secret:
        return {"mfa_required": True, "temp_token": issue_temp_mfa_token(user)}
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()
    token = issue_access_token(user, mfa_at=0)
    return {
        "access_token": token,
        "mfa_setup_required": True,
        "expires_in": ttl,
    }


def complete_mfa(temp_token: str, totp_code: str) -> tuple[User, str]:
    user = decode_temp_mfa_token(temp_token)
    if not user.totp_secret:
        raise APIError(401, "UNAUTHORIZED", "Invalid credentials")
    secret = totp.decrypt_secret(user.totp_secret)
    if not totp.verify(secret, totp_code):
        raise APIError(401, "UNAUTHORIZED", "Invalid credentials")
    user.last_login_at = datetime.now(timezone.utc)
    db.session.commit()
    return user, issue_access_token(user)


def setup_mfa(user: User) -> dict:
    secret = totp.generate_secret()
    user.totp_secret_pending = totp.encrypt_secret(secret)
    db.session.commit()
    uri = totp.provisioning_uri(secret, user.email)
    return {"otpauth_uri": uri, "qr_code_base64": totp.qr_png_base64(uri)}


def confirm_mfa(user: User, totp_code: str) -> None:
    if not user.totp_secret_pending:
        raise APIError(400, "VALIDATION_ERROR", "MFA setup has not been started")
    secret = totp.decrypt_secret(user.totp_secret_pending)
    if not totp.verify(secret, totp_code):
        raise APIError(401, "UNAUTHORIZED", "Invalid credentials")
    user.totp_secret = user.totp_secret_pending
    user.totp_secret_pending = None
    db.session.commit()


def step_up_mfa(user: User, totp_code: str) -> str:
    if not user.totp_secret:
        raise APIError(403, "FORBIDDEN", "MFA is not enabled")
    secret = totp.decrypt_secret(user.totp_secret)
    if not totp.verify(secret, totp_code):
        raise APIError(401, "UNAUTHORIZED", "Invalid credentials")
    return issue_access_token(user)


def logout(_user: User) -> None:
    return None
