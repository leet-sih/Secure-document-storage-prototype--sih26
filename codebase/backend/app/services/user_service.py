"""
user_service.py — user lifecycle.

FUNCTIONS (see user_management_plan.md):
    create_user(data, created_by) -> (user, temporary_password)
        Generates a strong temp password, bcrypt-hashes it, is_first_login=True.
        RETURNS the temp password ONCE (never stored in plaintext).
    list_users() -> list[User]
    get_user(user_id) -> user
    change_password(user, current, new) -> None
        Verifies current, applies policy, clears is_first_login, stamps password_changed_at.
    update_user / deactivate_user -> deferred (see docs/TODO.md).

STORES: rows in users. Never returns password_hash/totp_secret to callers.
"""

import secrets
import string
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from app.core.audit_events import AuditEventType
from app.core.errors import APIError
from app.core.security import hash_password, verify_password
from app.extensions import db
from app.models.department import Department
from app.models.user import User
from app.services.audit_service import audit_service

_PW_POOLS = (string.ascii_uppercase, string.ascii_lowercase, string.digits, "!@#$%^&*")


def _generate_temp_password() -> str:
    """16-char password with at least one of each policy class. Never persisted in plaintext."""
    chars = [secrets.choice(pool) for pool in _PW_POOLS]
    all_chars = "".join(_PW_POOLS)
    chars += [secrets.choice(all_chars) for _ in range(12)]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def create_user(data: dict, created_by) -> tuple[User, str]:
    """Admin-provisioned account. RETURNS (user, temp_password). temp_password is shown once."""
    dept = db.session.get(Department, data["department_id"])
    if dept is None:
        raise APIError(404, "NOT_FOUND", "Department not found")

    temp_password = _generate_temp_password()
    user = User(
        email=data["email"].lower(),
        password_hash=hash_password(temp_password),
        full_name=data["full_name"],
        employee_id=data.get("employee_id"),
        role=data["role"],
        department_id=data["department_id"],
        is_first_login=True,
        is_active=True,
        created_by=created_by,
    )
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise APIError(409, "CONFLICT", "A user with that email or employee ID already exists")

    audit_service.record(
        AuditEventType.USER_CREATED.value,
        actor_user_id=created_by,
        target_type="user",
        target_id=user.id,
    )
    return user, temp_password


def list_users() -> list[User]:
    return User.query.order_by(User.created_at.desc()).all()


def get_user(user_id) -> User:
    user = db.session.get(User, user_id)
    if user is None:
        raise APIError(404, "NOT_FOUND", "User not found")
    return user


def change_password(user: User, current_password: str, new_password: str) -> None:
    """Verify current password, apply the new one, and clear the first-login flag."""
    if not verify_password(current_password, user.password_hash):
        raise APIError(401, "UNAUTHORIZED", "Current password is incorrect")
    if verify_password(new_password, user.password_hash):
        raise APIError(400, "VALIDATION_ERROR", "New password must be different from the current one")

    user.password_hash = hash_password(new_password)
    user.password_changed_at = datetime.now(timezone.utc)
    user.is_first_login = False
    db.session.commit()

    audit_service.record(
        AuditEventType.PASSWORD_CHANGED.value,
        actor_user_id=user.id,
        target_type="user",
        target_id=user.id,
    )


def update_user(user_id: str, data: dict, actor) -> User:
    user = get_user(user_id)

    old_role = user.role
    old_department_id = user.department_id

    if str(user.id) == str(actor.id) and "role" in data and data["role"] != user.role:
        raise APIError(400, "VALIDATION_ERROR", "Cannot change your own role")

    if "department_id" in data:
        department = db.session.get(Department, data["department_id"])
        if department is None:
            raise APIError(404, "NOT_FOUND", "Department not found")
        user.department_id = data["department_id"]

    if "role" in data:
        user.role = data["role"]

    if "full_name" in data:
        user.full_name = data["full_name"]

    db.session.commit()

    if user.role != old_role:
        audit_service.record(
            AuditEventType.ROLE_CHANGED.value,
            actor_user_id=actor.id,
            target_type="user",
            target_id=user.id,
            metadata={"old_role": old_role, "new_role": user.role},
        )

    if user.department_id != old_department_id:
        audit_service.record(
            AuditEventType.DEPARTMENT_CHANGED.value,
            actor_user_id=actor.id,
            target_type="user",
            target_id=user.id,
        )

    return user


def deactivate_user(user_id: str, actor) -> None:
    user = get_user(user_id)

    if str(user.id) == str(actor.id):
        raise APIError(400, "VALIDATION_ERROR", "Cannot deactivate your own account")

    if not user.is_active:
        return

    user.is_active = False
    db.session.commit()

    audit_service.record(
        AuditEventType.USER_DEACTIVATED.value,
        actor_user_id=actor.id,
        target_type="user",
        target_id=user.id,
    )


def activate_user(user_id: str, actor) -> None:
    user = get_user(user_id)

    if user.is_active:
        return

    user.is_active = True
    db.session.commit()

    audit_service.record(
        AuditEventType.USER_ACTIVATED.value,
        actor_user_id=actor.id,
        target_type="user",
        target_id=user.id,
    )