"""
models/ — SQLAlchemy ORM models. One file per table.

IMPORTANT: import every model here so Flask-Migrate can discover them for autogenerate.
When you add a model, add it to this list.

Tables:
    Department          departments        police station / court / forensic lab
    User                users              accounts, roles, MFA, lockout state
    Case                cases              top-level container for documents
    CaseMember          case_members       user<->case membership + per-case role
    Document            documents          document METADATA only (no content)
    DocumentChunk       document_chunks    per-chunk crypto metadata (ciphertext is in MinIO)
    AuditEvent          audit_events       append-only, hash-chained activity log
    DocumentSignature   document_signatures Ed25519 signatures on document integrity hash
    DocumentShareLink   document_share_links time-limited external share tokens (hashed)
"""

from app.models.department import Department            # noqa: F401
from app.models.user import User                        # noqa: F401
from app.models.case import Case                        # noqa: F401
from app.models.case_member import CaseMember           # noqa: F401
from app.models.document import Document                # noqa: F401
from app.models.document_chunk import DocumentChunk     # noqa: F401
from app.models.audit_event import AuditEvent           # noqa: F401
from app.models.document_signature import DocumentSignature      # noqa: F401
from app.models.document_share_link import DocumentShareLink     # noqa: F401
