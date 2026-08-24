"""
search_schemas.py — search query validation.

SearchQuerySchema -> validates GET /documents/search query params. Cross-field rule:
from_date must not be after to_date. Results are always scoped to accessible cases in
the service layer, never here.
"""

from marshmallow import Schema, fields, validate, validates_schema, ValidationError, RAISE

DOC_TYPES = [
    "FIR", "POLICE_REPORT", "INVESTIGATION_RECORD", "WITNESS_STATEMENT",
    "CHARGE_SHEET", "COURT_FILING", "EVIDENCE_RECORD", "FORENSIC_REPORT",
    "LEGAL_NOTICE", "JUDGMENT", "OTHER",
]
SORTS = ["created_at_desc", "created_at_asc", "filename", "size_desc"]


class SearchQuerySchema(Schema):
    class Meta:
        unknown = RAISE

    q = fields.Str(load_default=None, validate=validate.Length(max=200))
    doc_type = fields.Str(load_default=None, validate=validate.OneOf(DOC_TYPES))
    case_id = fields.UUID(load_default=None)
    from_date = fields.DateTime(load_default=None)
    to_date = fields.DateTime(load_default=None)
    uploaded_by = fields.UUID(load_default=None)
    tags = fields.List(fields.Str(), load_default=None)
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    limit = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))
    sort = fields.Str(load_default="created_at_desc", validate=validate.OneOf(SORTS))

    @validates_schema
    def _date_order(self, data, **kwargs):
        if data.get("from_date") and data.get("to_date") and data["from_date"] > data["to_date"]:
            raise ValidationError("from_date must be before to_date")
