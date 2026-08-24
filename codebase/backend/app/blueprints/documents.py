"""
documents.py — upload / list / download / preview / delete. Prefix: /api/v1

ROUTES:
    POST /cases/{case_id}/documents   [SUPER_ADMIN, CASE_OFFICER]  multipart upload (rate-limited)
        Streams the `file` part into document_service.upload_document. Blocks if case
        is CLOSED/ARCHIVED. Records DOCUMENT_UPLOADED.
    GET  /cases/{case_id}/documents   [members]  list metadata (no content)
    GET  /documents/{id}/download     [members]  pre-verify all chunks -> stream plaintext;
        Content-Disposition: attachment. IntegrityError -> 422 + INTEGRITY_VIOLATION.
        Records DOCUMENT_DOWNLOADED.
    GET  /documents/{id}/preview      [members]  server-rendered PDF/image preview (P1)
    DELETE /documents/{id}            [SUPER_ADMIN, CASE_OFFICER]  soft delete; DOCUMENT_DELETED
    PATCH /documents/{id}             [CASE_OFFICER]  title/tags

Stream uploads via request.stream — never request.get_data() (would buffer 500 MB in RAM).
See chunked_document_storage_plan.md + docs/EDGE_CASES.md sections 1 & 5.
"""

from flask import Blueprint

documents_bp = Blueprint("documents", __name__)

# TODO: implement routes.
# from app.core.rbac import require_roles, Role
# from app.extensions import limiter
# from app.core.rate_limit import UPLOAD_LIMITS
# from app.schemas.document_schemas import DocumentUploadSchema, DocumentPatchSchema, DocumentMetadataSchema
# from app.services import document_service, case_service
