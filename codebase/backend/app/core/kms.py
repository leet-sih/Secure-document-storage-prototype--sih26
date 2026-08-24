"""
kms.py — key management for document master keys.  (PROTOTYPE: local file store)

RESPONSIBILITY:
    Store/fetch/delete the 32-byte master key for a document, keyed by document_id.
    Master keys NEVER go into PostgreSQL — they live in a separate keystore. That separation
    is the whole point: a stolen database is useless without these keys.

PROTOTYPE IMPLEMENTATION:
    Keys are written to individual files under KMS_DIR (default ./data/keys), each file
    AES-wrapped with the app SECRET_KEY. Simple, persistent, no extra services.
    Production swaps this module for HashiCorp Vault — the three functions below keep the
    same signatures, so document_service never changes. (See docs/ARCHITECTURE.md.)

Reference: ../../feature_plans/chunked_document_storage_plan.md
"""

# Implementation notes for whoever builds this (small + straightforward):
#   store_key: encrypt `key` with SECRET_KEY (AESGCM), write to KMS_DIR/{document_id}.key
#   get_key:   read + decrypt that file
#   delete_key: os.remove the file (ignore if missing)


def store_key(document_id: str, key: bytes) -> None:
    """Persist a document's master key (AES-wrapped) to KMS_DIR/{document_id}.key. TODO."""
    raise NotImplementedError


def get_key(document_id: str) -> bytes:
    """RETURNS the master key. Raise FileNotFoundError if missing (caller -> 404/500). TODO."""
    raise NotImplementedError


def delete_key(document_id: str) -> None:
    """Remove the key file (on hard-delete / failed-upload cleanup). Idempotent. TODO."""
    raise NotImplementedError
