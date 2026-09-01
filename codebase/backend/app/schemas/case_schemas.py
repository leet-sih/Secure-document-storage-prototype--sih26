"""
case_schemas.py — case create/update, membership, transfer, and all response shapes.

Input schemas (unknown=RAISE):
    CaseCreateSchema      -> POST /cases
    CasePatchSchema       -> PATCH /cases/{id}
    CaseMemberAddSchema   -> POST /cases/{id}/members
    CaseTransferSchema    -> POST /cases/{id}/transfer

Output schemas (dump-only, no unknown=RAISE needed):
    CaseListItemSchema    -> GET /cases items[]
    CaseDetailSchema      -> POST/GET/PATCH/transfer responses
    CaseMemberSchema      -> members[] rows
    TimelineEventSchema   -> GET /cases/{id}/timeline events[]
    TransferOptionsSchema -> GET /cases/{id}/transfer-options
"""

from marshmallow import Schema, fields, validate, RAISE

STATUSES = ["OPEN", "UNDER_INVESTIGATION", "CLOSED", "ARCHIVED"]
PRIORITIES = ["LOW", "NORMAL", "HIGH", "CRITICAL"]
CASE_MEMBER_ROLES = ["CASE_OFFICER", "INVESTIGATOR", "PROSECUTOR", "VIEWER"]


class _Base(Schema):
    class Meta:
        unknown = RAISE


# ── Input schemas ──────────────────────────────────────────────────────────────

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
    status = fields.Str(validate=validate.OneOf(STATUSES))


class CaseMemberAddSchema(_Base):
    user_id = fields.UUID(required=True)
    role = fields.Str(required=True, validate=validate.OneOf(CASE_MEMBER_ROLES))


class CaseTransferSchema(_Base):
    to_department_id = fields.UUID(required=True)
    new_lead_officer_id = fields.UUID(required=True)


# ── Response building blocks ───────────────────────────────────────────────────

class _UserBriefSchema(Schema):
    id = fields.UUID(dump_only=True)
    email = fields.Str(dump_only=True)
    full_name = fields.Str(dump_only=True)
    role = fields.Str(dump_only=True)


class _DeptBriefSchema(Schema):
    id = fields.UUID(dump_only=True)
    name = fields.Str(dump_only=True)


# ── Response schemas ───────────────────────────────────────────────────────────

class CaseMemberSchema(Schema):
    user_id = fields.UUID(dump_only=True)
    email = fields.Str(dump_only=True)
    full_name = fields.Str(dump_only=True)
    role = fields.Str(dump_only=True)
    department = fields.Str(dump_only=True)
    added_at = fields.DateTime(dump_only=True)


class CaseListItemSchema(Schema):
    id = fields.UUID(dump_only=True)
    case_number = fields.Str(dump_only=True)
    title = fields.Str(dump_only=True)
    status = fields.Str(dump_only=True)
    priority = fields.Str(dump_only=True)
    category = fields.Str(dump_only=True, allow_none=True)
    document_count = fields.Int(dump_only=True)
    member_count = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)


class CaseDetailSchema(Schema):
    id = fields.UUID(dump_only=True)
    case_number = fields.Str(dump_only=True)
    title = fields.Str(dump_only=True)
    description = fields.Str(dump_only=True, allow_none=True)
    status = fields.Str(dump_only=True)
    priority = fields.Str(dump_only=True)
    category = fields.Str(dump_only=True, allow_none=True)
    created_by = fields.Nested(_UserBriefSchema, dump_only=True)
    lead_officer = fields.Nested(_UserBriefSchema, dump_only=True, allow_none=True)
    department = fields.Nested(_DeptBriefSchema, dump_only=True)
    members = fields.List(fields.Nested(CaseMemberSchema), dump_only=True)
    document_summary = fields.Dict(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    closed_at = fields.DateTime(dump_only=True, allow_none=True)
    archived_at = fields.DateTime(dump_only=True, allow_none=True)


class TimelineEventSchema(Schema):
    id = fields.Int(dump_only=True)
    event_type = fields.Str(dump_only=True)
    actor = fields.Nested(_UserBriefSchema, dump_only=True, allow_none=True)
    target_type = fields.Str(dump_only=True, allow_none=True)
    metadata = fields.Dict(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class _OfficerOptionSchema(Schema):
    id = fields.UUID(dump_only=True)
    full_name = fields.Str(dump_only=True)
    email = fields.Str(dump_only=True)
    department_id = fields.UUID(dump_only=True)


class TransferOptionsSchema(Schema):
    departments = fields.List(fields.Nested(_DeptBriefSchema), dump_only=True)
    officers = fields.List(fields.Nested(_OfficerOptionSchema), dump_only=True)


# Keep old name as alias so any existing import doesn't break
CaseResponseSchema = CaseListItemSchema
