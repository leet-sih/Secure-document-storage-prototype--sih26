"""
signature_schemas.py — signature response serialization.

SignatureResponseSchema -> for POST /sign and GET /signatures list items.
VerifyResultSchema     -> one entry in the POST /verify result list.
VerifyResponseSchema   -> full POST /verify response body.

NEVER dumps signature_hex, signed_payload_hash, or integrity_hash_at_signing — those are
internal cryptographic values. Signing takes no request body (identity is the JWT).
"""

from marshmallow import Schema, fields


class _SignerBriefSchema(Schema):
    id = fields.UUID(dump_only=True)
    full_name = fields.Str(dump_only=True)
    role = fields.Str(dump_only=True)
    email = fields.Str(dump_only=True)


class SignatureResponseSchema(Schema):
    id = fields.UUID(dump_only=True)
    document_id = fields.UUID(dump_only=True)
    signer = fields.Method("_dump_signer", dump_only=True)
    signed_at = fields.DateTime(attribute="created_at", dump_only=True)
    is_valid = fields.Bool(dump_only=True, allow_none=True)
    last_verified_at = fields.DateTime(dump_only=True, allow_none=True)
    revoked_at = fields.DateTime(dump_only=True, allow_none=True)

    def _dump_signer(self, obj):
        from app.extensions import db
        from app.models.user import User
        user = db.session.get(User, obj.signer_user_id)
        if user is None:
            return {"id": str(obj.signer_user_id)}
        return _SignerBriefSchema().dump(user)


class VerifyResultSchema(Schema):
    signature_id = fields.Str(dump_only=True)
    signer_email = fields.Str(dump_only=True)
    is_valid = fields.Bool(dump_only=True)
    reason = fields.Str(dump_only=True, allow_none=True)


class VerifyResponseSchema(Schema):
    document_id = fields.UUID(dump_only=True)
    verified_at = fields.DateTime(dump_only=True)
    results = fields.List(fields.Nested(VerifyResultSchema), dump_only=True)
