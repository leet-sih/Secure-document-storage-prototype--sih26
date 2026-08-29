"""
auth.py — authentication routes. Prefix: /api/v1/auth
"""

from flask import Blueprint, current_app, request

from app.core.audit_events import AuditEventType
from app.core.errors import APIError
from app.core.rate_limit import LOGIN_LIMITS, MFA_LIMITS
from app.core.security import current_user_required, require_access_jwt
from app.extensions import limiter
from app.schemas.auth_schemas import LoginSchema, MFAConfirmSchema, MFAStepUpSchema, MFAVerifySchema
from app.services import auth_service
from app.services.audit_service import audit_service

auth_bp = Blueprint("auth", __name__)


def _ip() -> str | None:
    return request.remote_addr


@auth_bp.post("/login")
@limiter.limit(LOGIN_LIMITS)
def login():
    data = LoginSchema().load(request.get_json(silent=True) or {})
    try:
        user = auth_service.authenticate(data["email"], data["password"])
    except APIError as err:
        if err.status == 401:
            audit_service.record(AuditEventType.LOGIN_FAILED.value, ip_address=_ip())
        elif err.status == 423:
            audit_service.record(AuditEventType.ACCOUNT_LOCKED.value, ip_address=_ip())
        raise
    body = auth_service.begin_session(user)
    if not body.get("mfa_required"):
        audit_service.record(
            AuditEventType.LOGIN.value,
            actor_user_id=user.id,
            target_type="user",
            target_id=user.id,
            ip_address=_ip(),
            metadata={"mfa_setup_required": True},
        )
    return body


@auth_bp.post("/mfa/verify")
@limiter.limit(MFA_LIMITS)
def mfa_verify():
    data = MFAVerifySchema().load(request.get_json(silent=True) or {})
    try:
        user, token = auth_service.complete_mfa(data["temp_token"], data["totp_code"])
    except APIError:
        audit_service.record(AuditEventType.LOGIN_FAILED.value, ip_address=_ip())
        raise
    ttl = int(current_app.config.get("JWT_ACCESS_TTL_SECONDS", 28800))
    audit_service.record(
        AuditEventType.MFA_VERIFIED.value,
        actor_user_id=user.id,
        target_type="user",
        target_id=user.id,
        ip_address=_ip(),
    )
    audit_service.record(
        AuditEventType.LOGIN.value,
        actor_user_id=user.id,
        target_type="user",
        target_id=user.id,
        ip_address=_ip(),
    )
    return {"access_token": token, "expires_in": ttl}


@auth_bp.get("/mfa/setup")
@require_access_jwt
def mfa_setup():
    user = current_user_required()
    return auth_service.setup_mfa(user)


@auth_bp.post("/mfa/confirm")
@require_access_jwt
def mfa_confirm():
    data = MFAConfirmSchema().load(request.get_json(silent=True) or {})
    user = current_user_required()
    auth_service.confirm_mfa(user, data["totp_code"])
    audit_service.record(
        AuditEventType.MFA_ENABLED.value,
        actor_user_id=user.id,
        target_type="user",
        target_id=user.id,
        ip_address=_ip(),
    )
    return ("", 204)


@auth_bp.post("/mfa/step-up")
@limiter.limit(MFA_LIMITS)
@require_access_jwt
def mfa_step_up():
    data = MFAStepUpSchema().load(request.get_json(silent=True) or {})
    user = current_user_required()
    try:
        token = auth_service.step_up_mfa(user, data["totp_code"])
    except APIError as err:
        if err.status == 401:
            audit_service.record(
                AuditEventType.MFA_STEP_UP_FAILED.value,
                actor_user_id=user.id,
                ip_address=_ip(),
            )
        raise
    audit_service.record(
        AuditEventType.MFA_STEP_UP_VERIFIED.value,
        actor_user_id=user.id,
        target_type="user",
        target_id=user.id,
        ip_address=_ip(),
    )
    return {"access_token": token}


@auth_bp.post("/logout")
@require_access_jwt
def logout():
    user = current_user_required()
    auth_service.logout(user)
    audit_service.record(
        AuditEventType.LOGOUT.value,
        actor_user_id=user.id,
        ip_address=_ip(),
    )
    return ("", 204)
