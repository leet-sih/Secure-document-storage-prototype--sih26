"""
users.py — user administration + self-service. Prefix: /api/v1/users

Routes:
    GET  /me                    -> current user (any authenticated user)
    POST /me/change-password    -> change own password (forced on first login)
    GET  /                      -> list users (SUPER_ADMIN: full; CASE_OFFICER: slim picker view)
    POST /                      -> create user / admin-provisioned signup (SUPER_ADMIN + MFA step-up)
    GET  /departments           -> departments (SUPER_ADMIN + CASE_OFFICER — needed for member picker)
    PATCH /<id>                 -> edit role/dept/name (SUPER_ADMIN + MFA step-up)
    DELETE /<id>                -> deactivate user (SUPER_ADMIN + MFA step-up)
    POST /<id>/activate         -> reactivate user (SUPER_ADMIN + MFA step-up)
"""

from flask import Blueprint, request

from app.core.rbac import Role, require_recent_mfa, require_roles
from app.core.security import current_user_required, require_access_jwt
from app.schemas.user_schemas import (
    DepartmentSchema,
    PasswordChangeSchema,
    UserCreateSchema,
    UserPatchSchema,
    UserResponseSchema,
    UserSlimSchema,
)
from app.models.department import Department
from app.services import user_service

users_bp = Blueprint("users", __name__)


@users_bp.get("/me")
@require_access_jwt
def me():
    user = current_user_required()
    return UserResponseSchema().dump(user)


@users_bp.post("/me/change-password")
@require_access_jwt
def change_password():
    data = PasswordChangeSchema().load(request.get_json(silent=True) or {})
    user = current_user_required()
    user_service.change_password(user, data["current_password"], data["new_password"])
    return ("", 204)


@users_bp.get("")
@require_roles(Role.SUPER_ADMIN, Role.CASE_OFFICER)
def list_users(current_user):
    users = user_service.list_users()
    schema = UserSlimSchema(many=True) if current_user.role == Role.CASE_OFFICER.value else UserResponseSchema(many=True)
    return {"users": schema.dump(users)}


@users_bp.patch("/<uuid:user_id>")
@require_roles(Role.SUPER_ADMIN)
@require_recent_mfa()
def update_user(user_id, current_user):
    data = UserPatchSchema().load(request.get_json(silent=True) or {})
    user = user_service.update_user(str(user_id), data, current_user)
    return UserResponseSchema().dump(user)


@users_bp.delete("/<uuid:user_id>")
@require_roles(Role.SUPER_ADMIN)
@require_recent_mfa()
def deactivate_user(user_id, current_user):
    user_service.deactivate_user(str(user_id), current_user)
    return ("", 204)


@users_bp.post("/<uuid:user_id>/activate")
@require_roles(Role.SUPER_ADMIN)
@require_recent_mfa()
def activate_user(user_id, current_user):
    user_service.activate_user(str(user_id), current_user)
    return ("", 204)


@users_bp.post("")
@require_roles(Role.SUPER_ADMIN)
@require_recent_mfa()
def create_user(current_user):
    data = UserCreateSchema().load(request.get_json(silent=True) or {})
    user, temp_password = user_service.create_user(data, created_by=current_user.id)
    return {"user": UserResponseSchema().dump(user), "temp_password": temp_password}, 201


@users_bp.get("/departments")
@require_roles(Role.SUPER_ADMIN, Role.CASE_OFFICER)
def list_departments(current_user):
    departments = Department.query.order_by(Department.name.asc()).all()
    return {"departments": DepartmentSchema(many=True).dump(departments)}
