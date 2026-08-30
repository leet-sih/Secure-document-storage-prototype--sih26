"""
kms.py — key management for document master keys.
PRAMAAN — Secure Evidence Vault (leet / SIH26)

RESPONSIBILITY:
    Store/fetch/delete the 32-byte master key for a document, keyed by document_id.
    Master keys NEVER go into PostgreSQL — they live in a separate keystore. That separation
    is the whole point: a stolen database is useless without these keys.

PROTOTYPE IMPLEMENTATION:
    Keys are written to individual files under KMS_DIR (default ./data/keys), each file
    AES-wrapped with the dedicated KMS_WRAPPING_KEY env var.

    CRITICAL: KMS_WRAPPING_KEY is NOT the same as SECRET_KEY.
      SECRET_KEY   — Flask session/cookie signing. If compromised, sessions are forgeable.
      KMS_WRAPPING_KEY — wraps document master keys. If compromised, encrypted documents
                         are exposed. These are completely different threat surfaces and
                         MUST be separate secrets.

    Production swaps this module for HashiCorp Vault — the three functions below keep the
    same signatures, so document_service never changes. (See docs/ARCHITECTURE.md.)

KMS BOUNDARY DECISION (see docs/ARCHITECTURE.md "KMS boundary"):
    Prototype: KMS runs on the app host, separate OS user + separate wrapping key.
    This is option (b) — honest middle ground. The chunk store (Server B) has no key
    material; the database (Server A) has no key material. KMS lives with the app.
    Production: third host (HashiCorp Vault) — matches the architecture diagram fully.

Key lifecycle: see docs/SECURITY.md "Key lifecycle".

Reference: feature_plans/chunked_document_storage_plan.md
"""

from pathlib import Path

from flask import current_app

from app.core.crypto import normalize_wrapping_key, unwrap_key, wrap_key


def _wrapping_key() -> bytes:
    return normalize_wrapping_key(current_app.config["KMS_WRAPPING_KEY"])


def _key_path(document_id: str) -> Path:
    return Path(current_app.config["KMS_DIR"]) / f"{document_id}.key"


def store_key(document_id: str, key: bytes) -> None:
    """Persist a document's master key (AES-wrapped with KMS_WRAPPING_KEY) to
    KMS_DIR/{document_id}.key."""
    path = _key_path(document_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = wrap_key(_wrapping_key(), key)
    path.write_bytes(blob)


def get_key(document_id: str) -> bytes:
    """Return the master key for document_id. Raises FileNotFoundError if missing."""
    path = _key_path(document_id)
    if not path.is_file():
        raise FileNotFoundError(document_id)
    return unwrap_key(_wrapping_key(), path.read_bytes())


def delete_key(document_id: str) -> None:
    """Remove the key file (on hard-delete / failed-upload cleanup). Idempotent."""
    path = _key_path(document_id)
    try:
        path.unlink()
    except FileNotFoundError:
        return
