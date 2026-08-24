"""
maintenance.py — housekeeping helpers (called on demand, not scheduled).

sweep_orphaned_documents() -> int
    Find documents stuck in UPLOADING/FAILED for > 1 hour and purge their side effects:
    chunk_store.delete_document(id), kms.delete_key(id), and remove the document + chunk rows.
    Prevents orphaned ciphertext and dangling keys after a failed/abandoned upload.
    RETURNS: count cleaned up.

PROTOTYPE: run manually (e.g. wire to a `flask cleanup` CLI command or a SUPER_ADMIN route).
Production schedules this via Celery beat. See chunked_document_storage_plan.md +
docs/EDGE_CASES.md 1.7.
"""


def sweep_orphaned_documents() -> int:
    raise NotImplementedError
