"""
rbac.py — role-based access control.

RESPONSIBILITY:
    Provide the Role enum and the @require_roles(...) decorator used on protected routes.
    The decorator loads the current user from the JWT, checks their SYSTEM role, records
    an UNAUTHORIZED_ACCESS_ATTEMPT audit event on failure, and injects current_user into
    the handler.

NOTE: system-role checks here are coarse. Fine-grained CASE-level access (is this user a
member of this case?) is enforced in case_service — and returns 404, not 403.

Reference: ../../docs/SECURITY.md
"""

from enum import Enum
from functools import wraps

from flask import abort
from flask_jwt_extended import get_jwt_identity

from app.models.user import User
from app.services.audit_service import audit_service
from app.core.audit_events import AuditEventType


class Role(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    CASE_OFFICER = "CASE_OFFICER"
    INVESTIGATOR = "INVESTIGATOR"
    PROSECUTOR = "PROSECUTOR"
    AUDITOR = "AUDITOR"
    VIEWER = "VIEWER"


def require_roles(*roles: Role):
    """Guard a route so only the listed roles may enter. Injects current_user kwarg.
    Assumes @jwt_required() has already run. Returns 403 + audit on role mismatch."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = User.query.get_or_404(user_id)
            if not user.is_active:
                abort(403, description="Account is deactivated")
            if user.role not in [r.value for r in roles]:
                audit_service.record(
                    AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT.value,
                    actor_user_id=user_id,
                )
                abort(403, description="Insufficient permissions")
            return func(*args, current_user=user, **kwargs)
        return wrapper
    return decorator
