# Edge Cases & Failure Modes — Secure DMS (leet / SIH26)

Per-feature edge cases live in each `feature_plans/*_plan.md`. This file catalogs the
**cross-cutting** ones — the interactions between components, infrastructure failures, and
concurrency hazards that no single feature plan owns. Review this before the demo: several of
these are exactly what a judge will try to break.

Legend: **[P0]** must handle for the prototype · **[P1]** handle if time allows · **[doc]** document the limitation, don't fix now.

---

## 1. Storage & Crypto Integrity

| # | Scenario | Expected Behaviour | Priority |
|---|----------|--------------------|----------|
| 1.1 | **Vault/KMS unreachable during upload** | Abort the upload before writing any chunk to MinIO; return 503; nothing persisted. Never fall back to storing the key in the DB or on disk. | P0 |
| 1.2 | **Vault/KMS unreachable during download** | Return 503 "temporarily unavailable". Do not serve a partially decrypted file. | P0 |
| 1.3 | **MinIO write fails after N of M chunks uploaded** | Roll back: delete already-uploaded chunk objects (`prefix doc-chunks/{doc_id}/`), delete the Vault key, mark document `FAILED`, rollback DB. No orphan chunks. | P0 |
| 1.4 | **MinIO object missing at download time** (chunk deleted out-of-band) | `total_chunks` mismatch or fetch error → 422 INTEGRITY_VIOLATION, audit it. Never emit a truncated file. | P0 |
| 1.5 | **Ciphertext modified in MinIO** | `SHA256(ciphertext) != chunk_hash` (or GCM `InvalidTag`) → abort 422 before streaming, audit INTEGRITY_VIOLATION. | P0 |
| 1.6 | **Chunk rows reordered / index tampered in DB** | Overall `integrity_hash` (SHA256 of ordered chunk hashes) won't match → 422. | P0 |
| 1.7 | **Orphaned `UPLOADING` documents** (client disconnected mid-upload) | Hourly Celery sweep: documents stuck `UPLOADING`/`FAILED` > 1h → purge their MinIO objects + Vault key + rows. | P1 |
| 1.8 | **Empty file (0 bytes) uploaded** | Reject at validation: min size 1 byte. A 0-chunk document is meaningless. | P1 |
| 1.9 | **File whose magic bytes disagree with extension** (`.pdf` that is really an `.exe`) | MIME is decided by magic bytes (`python-magic`), not the filename/header → reject if not allowlisted. | P0 |
| 1.10 | **Duplicate identical file uploaded twice** | Prototype: stored as two independent documents (no dedup). Convergent-encryption dedup is roadmap (R3). | doc |

---

## 2. Concurrency & Ordering

| # | Scenario | Expected Behaviour | Priority |
|---|----------|--------------------|----------|
| 2.1 | **Audit chain append across Gunicorn workers** | Serialize with `pg_advisory_xact_lock` — an in-process `threading.Lock` does NOT hold across worker processes. See audit_trail_plan.md. | P0 |
| 2.2 | **Two requests spend the last use of a share link** | Atomic conditional `UPDATE ... SET use_count = use_count+1 WHERE use_count < max_uses RETURNING id`; the loser gets 410. | P0 |
| 2.3 | **Refresh-token rotation race (multi-tab)** | First use rotates+deletes the token; second gets 401. Client single-flights refresh; server keeps a ~10s grace key. See auth_plan.md. | P1 |
| 2.4 | **Same user signs a document twice concurrently** | `UNIQUE(document_id, signer_user_id)` → one insert wins, the other gets 409. | P0 |
| 2.5 | **Case member removed while they have an in-flight request** | Access is re-evaluated per request; the next request 404s. An already-streaming download completes. | P1 |
| 2.6 | **Two officers edit the same case row** | Last-write-wins on scalar fields for the prototype; note as a limitation (no optimistic locking yet). | doc |

---

## 3. Auth, Session & Identity

| # | Scenario | Expected Behaviour | Priority |
|---|----------|--------------------|----------|
| 3.1 | **Access token expires mid-download** | Auth checked once at request start; long transfer completes. Do not re-check mid-stream. | P0 |
| 3.2 | **User deactivated mid-session** | Stateless JWT stays valid ≤15 min; `is_active` re-checked on every request → next request 401. | P0 |
| 3.3 | **Password changed → all sessions killed** | Delete all `refresh:{user_id}:*` in Redis; other devices fall back to login on next refresh. | P0 |
| 3.4 | **bcrypt 72-byte truncation** | Cap password at 72 bytes in schema (bytes, not chars). See SECURITY.md. | P0 |
| 3.5 | **TOTP replay within its 30s window** | Mark used codes in Redis (`totp_used:{uid}:{code}`, 60s TTL); reuse → 401. | P0 |
| 3.6 | **Device clock skew for TOTP** | `valid_window=1` (±30s). Beyond that, reject and tell the user to sync their clock. | P0 |
| 3.7 | **First-login user tries to reach any page before changing password** | Restricted token scope = `password_change_only`; guard redirects to `/change-password`. | P0 |
| 3.8 | **SUPER_ADMIN demotes/deactivates themselves** | Blocked (400) — must transfer SUPER_ADMIN to another active user first. Prevents lockout of the whole system. | P0 |

---

## 4. Access Scoping (information-leak prevention)

| # | Scenario | Expected Behaviour | Priority |
|---|----------|--------------------|----------|
| 4.1 | **Non-member requests a case/document that exists** | Return **404**, never 403 — 403 confirms existence. Applies to cases, documents, search filters, share info. | P0 |
| 4.2 | **Search with `case_id` the user can't see** | Silently return empty results, not an error. | P0 |
| 4.3 | **User with zero accessible cases** | Empty lists everywhere; never leak any case/document ID. | P0 |
| 4.4 | **Error messages / stack traces** | 500s return a generic body + `request_id`; real details go to server logs only. Debug mode OFF in the demo build. | P0 |
| 4.5 | **Enumerable IDs** | All public-facing IDs are UUIDv4 (documents, cases, users). Audit `id` is BIGSERIAL but never exposed via a guessable public route. | P0 |

---

## 5. Input & Payload Limits

| # | Scenario | Expected Behaviour | Priority |
|---|----------|--------------------|----------|
| 5.1 | **Upload exceeds MAX_FILE_SIZE (500 MB)** | Reject early (Nginx `client_max_body_size` + app check) with 413/400 before buffering the whole body. | P0 |
| 5.2 | **Nginx/Gunicorn timeout on a large upload** | Set `client_body_timeout`, `proxy_read_timeout`, and Gunicorn `--timeout` high enough for 500 MB, or use chunked/resumable upload. Document the chosen ceiling. | P1 |
| 5.3 | **Marshmallow receives unexpected fields** | `Meta.unknown = RAISE` → 400, so a client can't smuggle e.g. `role` into a self-profile update. | P0 |
| 5.4 | **Oversized search query / pagination** | `q` capped at 200 chars; `limit` capped at 100; invalid `from_date > to_date` → 400. | P0 |
| 5.5 | **Unicode / RTL / emoji in filenames** | Sanitize to `[a-zA-Z0-9._-]`, keep the original separately; never use the raw name in a filesystem path or `Content-Disposition` without encoding. | P0 |
| 5.6 | **Path traversal in filename** (`../../etc/passwd`) | Strip all path separators; MinIO key is derived from `{doc_id}/chunk_{i}`, never from the filename. | P0 |

---

## 6. Infra, Deploy & Demo-Day

| # | Scenario | Expected Behaviour | Priority |
|---|----------|--------------------|----------|
| 6.1 | **Cold `docker compose up` ordering** | Backend must wait for Postgres/Redis/MinIO/Vault healthchecks (`depends_on: condition: service_healthy`), else it crashes on first connect. | P0 |
| 6.2 | **Migrations not applied on fresh DB** | Run `flask db upgrade` on startup (entrypoint), idempotently. | P0 |
| 6.3 | **MinIO bucket doesn't exist on first run** | Startup script creates `doc-chunks` (private) if absent. | P0 |
| 6.4 | **Vault dev-mode restart wipes keys** | Dev Vault is in-memory — a restart makes every stored document undecryptable. For the demo, use the `env`/file KMS stub (persistent) or a Vault volume; note this loudly. | P0 |
| 6.5 | **Self-signed TLS cert rejected by browser** | Expected; document the "accept the warning" step in the demo script, or add the cert to the trust store on the demo machine. | P1 |
| 6.6 | **Seed/demo data missing** | Idempotent seed script: departments, one SUPER_ADMIN, sample users per role, 2 cases, sample documents. Re-runnable without duplicating. | P0 |
| 6.7 | **CORS blocks the SPA** | `CORS_ORIGINS` must list the exact frontend origin and allow credentials (cookies); a wildcard `*` is invalid with credentials. | P0 |
| 6.8 | **Redis eviction drops a refresh token / rate counter** | Use `noeviction` or a dedicated Redis DB for tokens so sessions aren't silently killed under memory pressure. | P1 |

---

## 7. Roadmap-Feature Guards (so half-built features can't misbehave)

| # | Scenario | Expected Behaviour | Priority |
|---|----------|--------------------|----------|
| 7.1 | **Playground opened for a document that gets deleted mid-session** | Session read fails gracefully → "document no longer available"; Redis context is dropped. | P1 |
| 7.2 | **OCR/embedding on an encrypted-but-non-text file** (e.g. video) | `ocr_status = NOT_APPLICABLE`; never block upload on OCR. | P1 |
| 7.3 | **Document deleted → stale vectors in Qdrant** | On soft-delete, also delete the document's points from Qdrant, else semantic search can surface a deleted doc's snippet. | P1 |
| 7.4 | **Semantic search bypassing case scope** | The Qdrant `case_id IN accessible_cases` payload filter is mandatory on every query — never search unfiltered. | P0 (when built) |

---

## Pre-Demo Smoke Test (run this end-to-end)

1. Fresh `docker compose up` → all services healthy, migrations applied, bucket + seed data present.
2. Log in as CASE_OFFICER → MFA → dashboard.
3. Create a case; upload a PDF, a scanned image, and a large-ish file.
4. Download the PDF → bytes are byte-identical to the original (checksum).
5. Corrupt one chunk object in MinIO → download now returns 422, audit shows INTEGRITY_VIOLATION.
6. Sign the document as two different users → both signatures verify; then tamper → both show invalid.
7. Share a document (24h, 1 use) → open in a private window, download once, second attempt → 410.
8. Log in as AUDITOR → view audit log → run `/audit/verify` → chain valid.
9. Log in as an INVESTIGATOR on a *different* case → confirm the first case is invisible (404, not 403).
