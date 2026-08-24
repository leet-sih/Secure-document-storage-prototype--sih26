"""
signature_schemas.py — signature response serialization.

SignatureResponseSchema -> serialization for GET /documents/{id}/signatures.
NEVER dumps signature_hex, signed_payload_hash, or integrity_hash_at_signing — those are
internal cryptographic values. Signing takes no request body (identity is the JWT).
"""

from marshmallow import Schema, fields


class SignatureResponseSchema(Schema):
    id = fields.UUID(dump_only=True)
    document_id = fields.UUID(dump_only=True)
    signer_user_id = fields.UUID(dump_only=True)
    is_valid = fields.Bool(dump_only=True, allow_none=True)
    last_verified_at = fields.DateTime(dump_only=True, allow_none=True)
    revoked_at = fields.DateTime(dump_only=True, allow_none=True)
    created_at = fields.DateTime(dump_only=True)
