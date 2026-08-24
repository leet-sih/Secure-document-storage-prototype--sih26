"""
user_schemas.py — user create/update/response.

UserCreateSchema     -> POST /users            (admin; NO password field — server generates temp)
UserPatchSchema      -> PATCH /users/{id}       (admin: role/dept/active/name)
UserSelfPatchSchema  -> PATCH /users/me         (self: name/phone ONLY — never role/dept)
PasswordChangeSchema -> POST /users/me/change-password
UserResponseSchema   -> serialization (never dumps password_hash/totp_secret)
"""

import re
from marshmallow import Schema, fields, validate, validates, ValidationError, RAISE

ROLES = ["SUPER_ADMIN", "CASE_OFFICER", "INVESTIGATOR", "PROSECUTOR", "AUDITOR", "VIEWER"]


class _Base(Schema):
    class Meta:
        unknown = RAISE


class UserCreateSchema(_Base):
    email = fields.Email(required=True)
    full_name = fields.Str(required=True, validate=validate.Length(min=2, max=200))
    employee_id = fields.Str(load_default=None, validate=validate.Length(max=50))
    role = fields.Str(required=True, validate=validate.OneOf(ROLES))
    department_id = fields.UUID(required=True)


class UserPatchSchema(_Base):
    role = fields.Str(validate=validate.OneOf(ROLES))
    department_id = fields.UUID()
    is_active = fields.Bool()
    full_name = fields.Str(validate=validate.Length(min=2, max=200))


class UserSelfPatchSchema(_Base):
    full_name = fields.Str(validate=validate.Length(min=2, max=200))
    phone = fields.Str(validate=validate.Regexp(r"^\+?[\d\s\-]{7,15}$"))


class PasswordChangeSchema(_Base):
    current_password = fields.Str(required=True, load_only=True)
    new_password = fields.Str(required=True, load_only=True)

    @validates("new_password")
    def _strength(self, value, **kwargs):
        if len(value) < 12:
            raise ValidationError("Password must be at least 12 characters")
        if len(value.encode("utf-8")) > 72:      # bcrypt truncates at 72 BYTES
            raise ValidationError("Password must be at most 72 bytes")
        if not re.search(r"[A-Z]", value):
            raise ValidationError("Must contain an uppercase letter")
        if not re.search(r"[a-z]", value):
            raise ValidationError("Must contain a lowercase letter")
        if not re.search(r"\d", value):
            raise ValidationError("Must contain a digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', value):
            raise ValidationError("Must contain a special character")


class UserResponseSchema(Schema):
    id = fields.UUID(dump_only=True)
    email = fields.Str(dump_only=True)
    full_name = fields.Str(dump_only=True)
    employee_id = fields.Str(dump_only=True)
    role = fields.Str(dump_only=True)
    department_id = fields.UUID(dump_only=True)
    is_active = fields.Bool(dump_only=True)
    mfa_enabled = fields.Bool(dump_only=True)
    last_login_at = fields.DateTime(dump_only=True)
    # NEVER dump: password_hash, totp_secret, signing keys
