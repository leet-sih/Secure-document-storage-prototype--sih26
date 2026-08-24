"""
tasks/ — maintenance helpers.  (PROTOTYPE: plain functions, no Celery)

    maintenance.py — cleanup of orphaned/failed uploads, run on demand or from a CLI command.

PROTOTYPE NOTE: no background worker/queue. If cleanup is needed we just call the function
(e.g. via `flask cleanup` or a small route). Production moves this to Celery + a schedule
(see docs/ARCHITECTURE.md). Roadmap jobs (OCR, embeddings) will also live here later.
"""
