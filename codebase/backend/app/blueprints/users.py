"""
users.py — user administration + self-service. Prefix: /api/v1/users

ROUTES:
    POST /                       [SUPER_ADMIN]  create user -> returns temporary_password ONCE
    GET  /                       [SUPER_ADMIN]  list/filter users
    GET  /{id}                   [SUPER_ADMIN or self]
    PATCH /{id}                  [SUPER_ADMIN]  role/dept/active/name
    GET  /me                     [auth]         current profile
    PATCH /me                    [auth]         name/phone only
    POST /me/change-password     [auth]         current+new -> revokes all sessions

Records USER_CREATED / ROLE_CHANGED / USER_DEACTIVATED / PASSWORD_CHANGED. See user_management_plan.md.
"""

from flask import Blueprint

users_bp = Blueprint("users", __name__)

# TODO: implement routes.
# from app.core.rbac import require_roles, Role
# from app.schemas.user_schemas import UserCreateSchema, UserPatchSchema, UserSelfPatchSchema, PasswordChangeSchema, UserResponseSchema
# from app.services import user_service
