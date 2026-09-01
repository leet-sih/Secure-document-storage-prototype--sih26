"""
auth_schemas.py — validates auth requests.

LoginSchema        -> POST /auth/login       {email, password}
MFAVerifySchema    -> POST /auth/mfa/verify  {temp_token, totp_code}
MFAConfirmSchema   -> POST /auth/mfa/confirm {totp_code}

Password strength itself is validated in user/change-password flows; login only checks
presence/length so we don't leak policy details to unauthenticated callers.
"""

from marshmallow import Schema, fields, validate, RAISE


class _Base(Schema):
    class Meta:
        unknown = RAISE


class LoginSchema(_Base):
    email = fields.Email(required=True, load_only=True)
    password = fields.Str(required=True, load_only=True, validate=validate.Length(min=1, max=128))


class MFAVerifySchema(_Base):
    temp_token = fields.Str(required=True)
    totp_code = fields.Str(required=True, validate=validate.Regexp(r"^\d{6}$"))


class MFAConfirmSchema(_Base):
    totp_code = fields.Str(required=True, validate=validate.Regexp(r"^\d{6}$"))


class MFAStepUpSchema(_Base):
    totp_code = fields.Str(required=True, validate=validate.Regexp(r"^\d{6}$"))
