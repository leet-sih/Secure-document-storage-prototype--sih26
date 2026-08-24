"""
audit_schemas.py — audit query params + safe response.

AuditQuerySchema     -> validates GET /audit query params
AuditEventSchema     -> serialization. NEVER dumps prev_hash/this_hash (internal integrity).
AuditVerifySchema    -> GET /audit/verify response shape
"""

from marshmallow import Schema, fields, validate, RAISE


class AuditQuerySchema(Schema):
    class Meta:
        unknown = RAISE
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    limit = fields.Int(load_default=50, validate=validate.Range(min=1, max=200))
    event_type = fields.Str(load_default=None)
    actor_id = fields.UUID(load_default=None)
    case_id = fields.UUID(load_default=None)
    target_type = fields.Str(load_default=None)
    from_date = fields.DateTime(load_default=None)
    to_date = fields.DateTime(load_default=None)


class AuditEventSchema(Schema):
    id = fields.Int(dump_only=True)
    event_type = fields.Str(dump_only=True)
    actor_user_id = fields.UUID(dump_only=True)
    target_type = fields.Str(dump_only=True)
    target_id = fields.UUID(dump_only=True)
    case_id = fields.UUID(dump_only=True)
    ip_address = fields.Str(dump_only=True)
    metadata = fields.Raw(attribute="event_metadata", dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    # NEVER dump: prev_hash, this_hash


class AuditVerifySchema(Schema):
    total_events = fields.Int(dump_only=True)
    chain_valid = fields.Bool(dump_only=True)
    first_break_at = fields.Int(dump_only=True, allow_none=True)
