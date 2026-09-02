"""
document_schemas.py — document upload metadata + safe response serialization.

DocumentUploadSchema   -> validates the non-file form fields of POST .../documents
DocumentPatchSchema    -> PATCH /documents/{id}  (title, tags)
DocumentMetadataSchema -> serialization. NEVER dumps integrity_hash, chunk IVs/hashes,
                          or anything that would help reconstruct the file.

The binary `file` part is handled directly in the blueprint (streamed), not by marshmallow.
"""

from marshmallow import Schema, fields, validate, RAISE

DOC_TYPES = [
    "FIR", "POLICE_REPORT", "INVESTIGATION_RECORD", "WITNESS_STATEMENT",
    "CHARGE_SHEET", "COURT_FILING", "EVIDENCE_RECORD", "FORENSIC_REPORT",
    "LEGAL_NOTICE", "JUDGMENT", "OTHER",
]


class _Base(Schema):
    class Meta:
        unknown = RAISE


class DocumentUploadSchema(_Base):
    doc_type = fields.Str(required=True, validate=validate.OneOf(DOC_TYPES))
    title = fields.Str(load_default=None, validate=validate.Length(max=255))
    tags = fields.List(
        fields.Str(validate=validate.Regexp(r"^[a-z0-9\-]{1,50}$")),
        load_default=list,
        validate=validate.Length(max=10),
    )


class DocumentPatchSchema(_Base):
    title = fields.Str(validate=validate.Length(max=255))
    tags = fields.List(fields.Str(validate=validate.Regexp(r"^[a-z0-9\-]{1,50}$")),
                       validate=validate.Length(max=10))


class DocumentMetadataSchema(Schema):
    id = fields.UUID(dump_only=True)
    case_id = fields.UUID(dump_only=True)
    filename = fields.Str(dump_only=True)
    title = fields.Str(dump_only=True)
    mime_type = fields.Str(dump_only=True)
    doc_type = fields.Str(dump_only=True)
    file_size_bytes = fields.Int(dump_only=True)
    total_chunks = fields.Int(dump_only=True)
    tags = fields.List(fields.Str(), dump_only=True)
    status = fields.Str(dump_only=True)
    uploaded_by = fields.UUID(dump_only=True)
    created_at = fields.DateTime(dump_only=True)


class DocumentPreviewSchema(_Base):
    document_id = fields.UUID(dump_only=True)
    mode = fields.Str(dump_only=True, validate=validate.OneOf(["pages", "text"]))
    pages_png_base64 = fields.List(fields.Str(), dump_only=True)
    text = fields.Str(dump_only=True, allow_none=True)
    page_count = fields.Int(dump_only=True)
    truncated = fields.Bool(dump_only=True)
