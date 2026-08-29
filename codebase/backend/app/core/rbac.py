"""
rbac.py — role-based access control + step-up MFA window.
"""

from datetime import datetime, timezone
from enum import Enum
from functools import wraps

from flask import current_app
from flask_jwt_extended import get_jwt

from app.core.audit_events import AuditEventType
from app.core.errors import APIError
from app.core.security import current_user_required, require_access_jwt
from app.services.audit_service import audit_service


class Role(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    CASE_OFFICER = "CASE_OFFICER"
    INVESTIGATOR = "INVESTIGATOR"
    PROSECUTOR = "PROSECUTOR"
    AUDITOR = "AUDITOR"
    VIEWER = "VIEWER"


def require_roles(*roles: Role):
    def decorator(func):
        @wraps(func)
        @require_access_jwt
        def wrapper(*args, **kwargs):
            user = current_user_required()
            if user.role not in [r.value for r in roles]:
                audit_service.record(
                    AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT.value,
                    actor_user_id=user.id,
                )
                raise APIError(403, "FORBIDDEN", "Insufficient permissions")
            return func(*args, current_user=user, **kwargs)

        return wrapper

    return decorator


def require_recent_mfa(minutes: int | None = None):
    """401 MFA_REQUIRED when JWT mfa_at is older than the step-up window."""

    def decorator(func):
        @wraps(func)
        @require_access_jwt
        def wrapper(*args, **kwargs):
            user = current_user_required()
            window = minutes if minutes is not None else int(current_app.config.get("MFA_STEP_UP_MINUTES", 15))
            mfa_at = int(get_jwt().get("mfa_at") or 0)
            now = int(datetime.now(timezone.utc).timestamp())
            if now - mfa_at > window * 60:
                raise APIError(401, "MFA_REQUIRED", "Please verify your identity to continue.")
            return func(*args, current_user=user, **kwargs)

        return wrapper

    return decorator
