"""
kms.py — key management for document master keys.
PRAMAAN — Secure Evidence Vault (leet / SIH26)

RESPONSIBILITY:
    Store/fetch/delete the 32-byte master key for a document, keyed by document_id.

PROTOTYPE IMPLEMENTATION (Postgres keystore — see spec below):
    Keys are stored in the `document_keys` table, each AES-256-GCM WRAPPED with the dedicated
    KMS_WRAPPING_KEY env var. Only the wrapped form (+ its IV) ever touches the DB — the
    plaintext master key never does. A stolen database dump therefore yields only wrapped keys
    that cannot be unwrapped without BOTH the separate KMS_WRAPPING_KEY (env, not in the DB)
    AND the ciphertext (chunk store, not in the DB).

    NOTE: this is a deliberate deviation from feature_plans/chunked_document_storage_plan.md,
    which used a local FILE KMS. Storing keys in Postgres was a product decision; keeping them
    WRAPPED keeps it compliant with CLAUDE.md ("app-encrypted only"). The three functions below
    keep their original signatures, so document_service is agnostic to where keys live.
    See feature_plans/specs/document_encryption_keystore_spec.md §5.4 for the threat analysis.

    CRITICAL: KMS_WRAPPING_KEY is NOT the same as SECRET_KEY.
      SECRET_KEY        — Flask session/cookie signing. If compromised, sessions are forgeable.
      KMS_WRAPPING_KEY  — wraps document master keys. If compromised (together with a DB dump),
                          encrypted documents are exposed. Different threat surfaces — MUST be
                          separate secrets.

    Production swaps this module for HashiCorp Vault — same signatures, so nothing else changes.

TRANSACTIONALITY:
    store_key/delete_key only flush() — they do NOT commit. The caller (document_service)
    owns the transaction, so the wrapped-key row commits/rolls back atomically with the
    documents + document_chunks rows. A failed upload can never leave an orphaned key.

Reference: feature_plans/specs/document_encryption_keystore_spec.md
"""

from flask import current_app

from app.core import crypto
from app.extensions import db
from app.models.document_key import DocumentKey


def store_key(document_id: str, key: bytes) -> None:
    """Wrap `key` under KMS_WRAPPING_KEY and persist it to document_keys for this document.
    Flushes (does not commit) — the caller owns the transaction."""
    iv, wrapped = crypto.wrap_master_key(current_app.config["KMS_WRAPPING_KEY"], key)
    row = DocumentKey(
        document_id=document_id,
        wrapped_key_hex=wrapped.hex(),
        wrap_iv_hex=iv.hex(),
    )
    db.session.add(row)
    db.session.flush()


def get_key(document_id: str) -> bytes:
    """Return the (unwrapped) master key for document_id.
    Raises FileNotFoundError if no key row exists (signature preserved from the file KMS)."""
    row = db.session.get(DocumentKey, document_id)
    if row is None:
        raise FileNotFoundError(f"no master key stored for document {document_id}")
    return crypto.unwrap_master_key(
        current_app.config["KMS_WRAPPING_KEY"],
        bytes.fromhex(row.wrap_iv_hex),
        bytes.fromhex(row.wrapped_key_hex),
    )


def delete_key(document_id: str) -> None:
    """Remove the wrapped-key row (on hard-delete / failed-upload cleanup). Idempotent.
    Flushes (does not commit) — the caller owns the transaction."""
    row = db.session.get(DocumentKey, document_id)
    if row is not None:
        db.session.delete(row)
        db.session.flush()
