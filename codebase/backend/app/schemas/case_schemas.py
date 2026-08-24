"""
case_schemas.py — case create/update, membership, and response.

CaseCreateSchema  -> POST /cases
CasePatchSchema   -> PATCH /cases/{id}          (includes status transitions)
CaseMemberAddSchema -> POST /cases/{id}/members
CaseResponseSchema / CaseDetailSchema -> serialization

NOTE: a case has priority/category — NOT doc_type (that belongs to documents).
"""

from marshmallow import Schema, fields, validate, RAISE

STATUSES = ["OPEN", "UNDER_INVESTIGATION", "CLOSED", "ARCHIVED"]
PRIORITIES = ["LOW", "NORMAL", "HIGH", "CRITICAL"]
CASE_MEMBER_ROLES = ["CASE_OFFICER", "INVESTIGATOR", "PROSECUTOR", "VIEWER"]


class _Base(Schema):
    class Meta:
        unknown = RAISE


class CaseCreateSchema(_Base):
    case_number = fields.Str(required=True, validate=[
        validate.Length(min=3, max=50),
        validate.Regexp(r"^[A-Za-z0-9\-\/]+$"),
    ])
    title = fields.Str(required=True, validate=validate.Length(min=3, max=255))
    description = fields.Str(load_default=None, validate=validate.Length(max=2000))
    priority = fields.Str(load_default="NORMAL", validate=validate.OneOf(PRIORITIES))
    category = fields.Str(load_default=None, validate=validate.Length(max=100))


class CasePatchSchema(_Base):
    title = fields.Str(validate=validate.Length(min=3, max=255))
    description = fields.Str(validate=validate.Length(max=2000))
    priority = fields.Str(validate=validate.OneOf(PRIORITIES))
    category = fields.Str(validate=validate.Length(max=100))
    status = fields.Str(validate=validate.OneOf(STATUSES))   # service enforces valid transitions


class CaseMemberAddSchema(_Base):
    user_id = fields.UUID(required=True)
    role = fields.Str(required=True, validate=validate.OneOf(CASE_MEMBER_ROLES))


class CaseResponseSchema(Schema):
    id = fields.UUID(dump_only=True)
    case_number = fields.Str(dump_only=True)
    title = fields.Str(dump_only=True)
    status = fields.Str(dump_only=True)
    priority = fields.Str(dump_only=True)
    category = fields.Str(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
