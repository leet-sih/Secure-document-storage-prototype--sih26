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

# Implementation notes for whoever builds this (small + straightforward):
#   store_key: encrypt `key` with KMS_WRAPPING_KEY (AESGCM), write to KMS_DIR/{document_id}.key
#   get_key:   read + decrypt that file using KMS_WRAPPING_KEY
#   delete_key: os.remove the file (ignore if missing)
#
# Use current_app.config["KMS_WRAPPING_KEY"] — NOT config["SECRET_KEY"].


def store_key(document_id: str, key: bytes) -> None:
    """Persist a document's master key (AES-wrapped with KMS_WRAPPING_KEY) to
    KMS_DIR/{document_id}.key. TODO."""
    raise NotImplementedError


def get_key(document_id: str) -> bytes:
    """Return the master key for document_id. Raises FileNotFoundError if missing. TODO."""
    raise NotImplementedError


def delete_key(document_id: str) -> None:
    """Remove the key file (on hard-delete / failed-upload cleanup). Idempotent. TODO."""
    raise NotImplementedError
