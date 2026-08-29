"""
users.py — user administration + self-service. Prefix: /api/v1/users

This feature implements GET /me only (needed after TOTP login). Other routes stay later.
"""

from flask import Blueprint

from app.core.security import current_user_required, require_access_jwt
from app.schemas.user_schemas import UserResponseSchema

users_bp = Blueprint("users", __name__)


@users_bp.get("/me")
@require_access_jwt
def me():
    user = current_user_required()
    return UserResponseSchema().dump(user)
