"""
sharing_schemas.py — share link creation, public access, and response.

ShareCreateSchema        -> POST /documents/{id}/share  (DOCUMENT scope)
CaseShareCreateSchema    -> POST /cases/{id}/share      (CASE_DOCUMENTS | CASE_FULL)
ShareAccessSchema        -> POST /share/{token}/download or /file/{doc_id}
ShareResponseSchema      -> serialization for the owner's share list (never leaks token_hash)
ShareInfoSchema          -> GET /share/{token}/info public response
"""

from marshmallow import Schema, fields, validate, validates_schema, ValidationError, RAISE


class _Base(Schema):
    class Meta:
        unknown = RAISE


class ShareCreateSchema(_Base):
    expires_in_hours = fields.Int(required=True, validate=validate.Range(min=1, max=48))
    max_uses = fields.Int(load_default=1, validate=validate.Range(min=-1, max=10))
    allowed_email = fields.Email(load_default=None)
    note = fields.Str(load_default=None, validate=validate.Length(max=500))
    allow_download = fields.Bool(load_default=True)


class CaseShareCreateSchema(_Base):
    share_scope = fields.Str(
        required=True,
        validate=validate.OneOf(["CASE_DOCUMENTS", "CASE_FULL"]),
    )
    expires_in_hours = fields.Int(required=True, validate=validate.Range(min=1, max=48))
    max_uses = fields.Int(load_default=1, validate=validate.Range(min=-1, max=10))
    allowed_email = fields.Email(load_default=None)
    note = fields.Str(load_default=None, validate=validate.Length(max=500))
    allow_download = fields.Bool(load_default=True)


class ShareAccessSchema(_Base):
    email = fields.Email(load_default=None)   # required only when the link has an email gate


class ShareResponseSchema(Schema):
    id = fields.UUID(dump_only=True)
    share_scope = fields.Str(dump_only=True)
    document_id = fields.UUID(dump_only=True, allow_none=True)
    case_id = fields.UUID(dump_only=True, allow_none=True)
    allowed_email = fields.Str(dump_only=True, allow_none=True)
    expires_at = fields.DateTime(dump_only=True)
    max_uses = fields.Int(dump_only=True)
    use_count = fields.Int(dump_only=True)
    is_revoked = fields.Bool(dump_only=True)
    note = fields.Str(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)
    # NEVER dump: token_hash
