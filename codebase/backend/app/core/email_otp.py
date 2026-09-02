"""
email_otp.py — In-memory OTP store + Gmail SMTP delivery for share link recipient verification.

generate_and_send(raw_token, email, hint) — 6-digit OTP, stored sha256'd, emailed via Gmail SMTP.
verify_or_raise(raw_token, email, otp)    — verify; raises APIError on wrong/expired/exhausted.
                                            No-op when email is absent (open link, no email entered).

Store key: sha256(raw_token + ":" + email_lower) — scoped per (link, recipient) pair.
OTPs are single-use (deleted on correct verification) and expire after OTP_TTL_MINUTES.
Max MAX_ATTEMPTS bad guesses before the entry is evicted (recipient must re-request).
"""

import hashlib
import secrets
import smtplib
import threading
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

from flask import current_app

from app.core.errors import APIError

_OTP_TTL_MINUTES = 10
_MAX_ATTEMPTS = 3

_store: dict[str, dict] = {}
_lock = threading.Lock()


def _key(raw_token: str, email: str) -> str:
    return hashlib.sha256(f"{raw_token}:{email.lower()}".encode()).hexdigest()


def _otp_hash(otp: str) -> str:
    return hashlib.sha256(otp.encode()).hexdigest()


def _evict_expired() -> None:
    now = datetime.now(timezone.utc)
    stale = [k for k, v in _store.items() if v["expires_at"] < now]
    for k in stale:
        del _store[k]


def generate_and_send(raw_token: str, email: str, hint: str = "document") -> None:
    """Generate a fresh OTP, store it, and send to *email* via Gmail SMTP."""
    otp = f"{secrets.randbelow(1_000_000):06d}"
    k = _key(raw_token, email)
    with _lock:
        _evict_expired()
        _store[k] = {
            "otp_hash": _otp_hash(otp),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=_OTP_TTL_MINUTES),
            "attempts": 0,
        }
    _send_gmail(email, otp, hint)


def verify_or_raise(raw_token: str, email: str | None, otp: str | None) -> None:
    """Verify OTP for the given (token, email) pair.

    No-op when *email* is falsy (open link with no email provided).
    Raises APIError(403, ...) on OTP absent / wrong / expired / exhausted.
    Deletes the store entry on success (single-use).
    """
    if not email:
        return
    if not otp:
        raise APIError(403, "OTP_REQUIRED", "An OTP is required — request one first")

    k = _key(raw_token, email)
    now = datetime.now(timezone.utc)
    with _lock:
        entry = _store.get(k)
        if not entry or entry["expires_at"] < now:
            _store.pop(k, None)
            raise APIError(403, "OTP_EXPIRED", "OTP has expired or was not requested — request a new one")
        if entry["attempts"] >= _MAX_ATTEMPTS:
            del _store[k]
            raise APIError(403, "OTP_EXHAUSTED", "Too many incorrect attempts — request a new OTP")
        if entry["otp_hash"] != _otp_hash(otp.strip()):
            entry["attempts"] += 1
            left = _MAX_ATTEMPTS - entry["attempts"]
            raise APIError(
                403, "OTP_INVALID",
                f"Incorrect OTP — {left} attempt{'s' if left != 1 else ''} remaining",
            )
        del _store[k]


def _send_gmail(to: str, otp: str, hint: str) -> None:
    user = current_app.config.get("GMAIL_USER", "")
    pwd = current_app.config.get("GMAIL_APP_PASSWORD", "")
    if not user or not pwd:
        raise APIError(503, "EMAIL_UNAVAILABLE", "Email delivery is not configured on this server")

    body = (
        f"Your PRAMAAN access code is:\n\n"
        f"    {otp}\n\n"
        f"This code is valid for {_OTP_TTL_MINUTES} minutes.\n"
        f"You are receiving this because access to a shared {hint} was requested on PRAMAAN.\n"
        f"If you did not request this, you can safely ignore this message.\n\n"
        f"— PRAMAAN Secure Evidence Vault"
    )
    msg = MIMEText(body)
    msg["Subject"] = "PRAMAAN access code"
    msg["From"] = f"PRAMAAN <{user}>"
    msg["To"] = to

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(user, pwd)
            smtp.sendmail(user, [to], msg.as_string())
    except smtplib.SMTPAuthenticationError as exc:
        raise APIError(503, "EMAIL_UNAVAILABLE", "Email delivery credentials are invalid") from exc
    except smtplib.SMTPException as exc:
        raise APIError(503, "EMAIL_SEND_FAILED", "Failed to send OTP email — please try again") from exc
