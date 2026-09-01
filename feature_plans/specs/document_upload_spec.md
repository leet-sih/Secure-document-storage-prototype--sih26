# Spec: Document upload (chunked encrypted ingest)

Sources: `feature_plans/chunked_document_storage_plan.md` (upload flow), `docs/TODO.md` Phase 3, `docs/ARCHITECTURE.md` (opaque keys + file KMS), `docs/API.md`, `docs/SECURITY.md`, `docs/EDGE_CASES.md` §1 and §5, `feature_plans/case_management_plan.md` (closed case), `design/github.md` + prototype (DocumentUploader). Canonical audit names: `app/core/audit_events.py`.

Prototype storage (do **not** implement the plan’s MinIO path keys or Vault): ciphertext via `storage/chunk_store.py` (local); master keys via `core/kms.py` wrapped with `KMS_WRAPPING_KEY`.

---

## What and why

A CASE_OFFICER or SUPER_ADMIN attaches a file to a case they can access. The server streams the file, splits it into 1 MB pieces, encrypts each piece with a unique HKDF-derived AES-256-GCM key, stores only ciphertext in the chunk store, stores the document master key in the file KMS, and writes metadata (not content) to PostgreSQL. The client gets document metadata back. That is the ingest path for the evidence vault.

User-facing: on the case Documents tab, drag-and-drop (or browse), required document type, optional title/tags, 500 MB client check, progress, POST multipart.

---

## Exact files

No other files. Do not implement download, list, preview, delete, PATCH, OCR, SFTP put/get, or orphan sweep on this branch.

**Create**

| Path | Why |
|------|-----|
| `feature_plans/specs/document_upload_spec.md` | This spec |
| `codebase/backend/migrations/versions/002_documents.py` | `documents` + `document_chunks` (Alembic `001` only has `departments`/`users`) |
| `codebase/backend/tests/documents/test_upload.py` | Names from the chunked-storage plan |
| `codebase/frontend/src/components/DocumentUploader.tsx` | Design map; listed in `components/README.md` |

**Modify**

| Path | Why |
|------|-----|
| `codebase/backend/app/core/crypto.py` | Add wrap/unwrap for KMS (AES-GCM). All raw crypto stays here. Chunk encrypt/HKDF already exist |
| `codebase/backend/app/core/kms.py` | `store_key` / `get_key` / `delete_key` — file I/O under `KMS_DIR` only |
| `codebase/backend/app/storage/chunk_store.py` | Local `put` / `get` / `delete_chunks`. Leave SFTP functions as stubs |
| `codebase/backend/app/services/document_service.py` | Implement `upload_document` + failure rollback only. Leave download/list/delete as `NotImplementedError` |
| `codebase/backend/app/blueprints/documents.py` | `POST /cases/<case_id>/documents` only |
| `codebase/backend/app/__init__.py` | Register `documents_bp` under `/api/v1`; ensure `KMS_DIR` and `CHUNK_STORAGE_DIR` exist |
| `codebase/backend/tests/test_crypto.py` | Unskip the existing tests (plan’s crypto contract) |

**Do not modify** (already match the contract): `models/document.py`, `models/document_chunk.py`, `schemas/document_schemas.py`, `core/rate_limit.py` (`UPLOAD_LIMITS`), `config.py` (`MAX_FILE_SIZE_MB`, `CHUNK_SIZE_BYTES`, `MAX_CONTENT_LENGTH`). Call `case_service.get_case_for_user` — do not implement case CRUD here.

**Frontend note:** `CaseDetailPage.tsx` does not exist. This branch ships `DocumentUploader` only; it is not mounted until case-detail exists. Do not create `CaseDetailPage` / `AppShell` / `DocumentList` here.

---

## Data model

No new tables beyond what the models already describe. Migration must create them.

**`documents`** (metadata only): `id`, `case_id` → `cases.id`, `filename` (sanitized), `original_filename`, `title`, `mime_type`, `doc_type`, `file_size_bytes`, `total_chunks`, `integrity_hash`, `status` (`UPLOADING` → `ACTIVE` or `FAILED`), `tags`, OCR/search columns left at defaults (`ocr_status=NOT_APPLICABLE`), `uploaded_by` → `users.id`, soft-delete columns unused on upload.

While the row is `UPLOADING`, `file_size_bytes`/`total_chunks` may be `0` and `integrity_hash` empty until success, then set before commit to `ACTIVE`.

**`document_chunks`:** `document_id`, `chunk_index`, `storage_key` (`secrets.token_hex(16)`, opaque, **not** `{doc_id}/chunk_NNNNNN`), `iv_hex`, `chunk_hash` (SHA-256 of ciphertext including GCM tag), `size_bytes` (plaintext length). Unique `(document_id, chunk_index)`.

**Not in DB:** master key, plaintext, ciphertext.

**`doc_type`:** `FIR`, `POLICE_REPORT`, `INVESTIGATION_RECORD`, `WITNESS_STATEMENT`, `CHARGE_SHEET`, `COURT_FILING`, `EVIDENCE_RECORD`, `FORENSIC_REPORT`, `LEGAL_NOTICE`, `JUDGMENT`, `OTHER`.

**FK blocker:** `case_id` references `cases`. Alembic `001` has no `cases` table. Tests can `create_all()` from models. A real `flask db upgrade` needs `cases` from the case-management migration (or that table present). Do not create the cases schema on this branch.

---

## API

```
POST /api/v1/cases/{case_id}/documents
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Roles:** `SUPER_ADMIN`, `CASE_OFFICER` (`@require_roles`). Other authenticated roles: 403 FORBIDDEN (system role, not case-scoping).

**Rate limit:** `UPLOAD_LIMITS` = 10 per minute per user.

**Form (non-file via `DocumentUploadSchema`, `unknown=RAISE`):**

| Field | Required | Notes |
|-------|----------|--------|
| `file` | yes | Binary; **not** marshmallow. Use `request.files["file"]` stream. Never `request.get_data()` / `request.json` |
| `doc_type` | yes | One of `DOC_TYPES` |
| `title` | no | Max 255 |
| `tags` | no | Max 10; each `^[a-z0-9\-]{1,50}$` |

**Processing (service):**

1. `get_case_for_user(case_id, uploader)` — miss → **404 NOT_FOUND** (never 403 for “wrong case”).
2. Case `CLOSED` or `ARCHIVED` → **409 CONFLICT** (“Case is closed — no new documents allowed” per case plan).
3. Reject 0-byte file.
4. MIME from **magic bytes** (`python-magic` on first 2048 bytes, then seek 0), not `Content-Type` or extension. Allowlist (`docs/SECURITY.md` / prototype copy; not `audio/mpeg`):

   `application/pdf`,  
   `application/vnd.openxmlformats-officedocument.wordprocessingml.document`,  
   `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`,  
   `image/jpeg`, `image/png`, `image/tiff`, `video/mp4`, `audio/wav`.

5. Enforce `MAX_FILE_SIZE_MB` (500). Flask `MAX_CONTENT_LENGTH` may 413 the body first (`EDGE_CASES` 5.1).
6. Sanitize filename: strip path components; keep `[a-zA-Z0-9._-]`; max 255. Store original separately. Storage keys are never derived from the filename.
7. Insert `Document(status=UPLOADING)`. Generate 32-byte master key; `kms.store_key`. If KMS fails: **503**, no chunks written (`EDGE_CASES` 1.1).
8. Loop `CHUNK_SIZE_BYTES` (1 MiB): `storage_key = token_hex(16)`; `derive_chunk_key` → `encrypt_chunk` → `sha256_hex(ciphertext)` → `chunk_store.put_chunk` → `DocumentChunk` row.
9. `integrity_hash = compute_integrity_hash(ordered hashes)`; set size, chunk count, `ACTIVE`; commit.
10. `audit_service.record(DOCUMENT_UPLOADED, …)` metadata: filename, size_bytes, chunks — no content, no keys.

**Success 201** body: `DocumentMetadataSchema` dump only (`id`, `case_id`, `filename`, `title`, `mime_type`, `doc_type`, `file_size_bytes`, `total_chunks`, `tags`, `status`, `uploaded_by`, `created_at`). Never `integrity_hash`, IVs, `storage_key`, chunk hashes.

**Errors** (`docs/API.md` envelope). 503 is in `EDGE_CASES` 1.1, not the API status table.

| Status | Code | When |
|--------|------|------|
| 400 | VALIDATION_ERROR | Bad/missing fields, empty file, MIME not allowlisted, extra form keys |
| 401 | UNAUTHORIZED | No/invalid JWT |
| 403 | FORBIDDEN | Authenticated but role not SUPER_ADMIN / CASE_OFFICER |
| 404 | NOT_FOUND | Unknown case **or** caller cannot access it |
| 409 | CONFLICT | Case CLOSED or ARCHIVED |
| 413 | (Flask) | Body larger than `MAX_CONTENT_LENGTH` |
| 429 | RATE_LIMITED | Upload limiter |
| 503 | (KMS) | KMS unreachable before any chunk write |
| 500 | INTERNAL_ERROR | Mid-pipeline failure after cleanup; generic message |

**Failure rollback** (`EDGE_CASES` 1.3): `chunk_store.delete_chunks` for keys written, `kms.delete_key`, mark `FAILED` or rollback the document row, no orphan ciphertext. Do not emit `DOCUMENT_UPLOADED`. Do not add `DOCUMENT_UPLOAD_FAILED` (not in `AuditEventType`).

Duplicate identical files: two independent documents (`EDGE_CASES` 1.10).

---

## Security

| Threat | Mitigation |
|--------|------------|
| Investigator/viewer uploads | Role decorator |
| Probe another officer’s case id | 404 via `get_case_for_user` |
| `virus.exe` named `report.pdf` | Magic-byte allowlist |
| Path traversal in filename | Sanitize; opaque `storage_key` |
| Buffer 500 MB in RAM | Stream 1 MB; no `get_data()` |
| Master key in Postgres or chunk dir | File KMS only; wrap with `KMS_WRAPPING_KEY` ≠ `SECRET_KEY` |
| Structured chunk filenames leak order | Opaque keys; order only in `chunk_index` |
| Inline crypto in the service | Service orchestrates; `crypto.py` only for AES/HKDF/hash/wrap |
| Logs leak evidence | Log ids, event type, size, chunk count |
| Closed case still writable | 409 |
| Partial write leaves plaintext | Never write plaintext to disk; rollback ciphertext + key |

Frontend does not decrypt. `apiFetch` already skips JSON `Content-Type` for `FormData`. Progress: XHR `onprogress` as in the chunked-storage plan (fetch has no upload progress).

---

## Edge cases (`docs/EDGE_CASES.md`)

| # | Behaviour this spec |
|---|---------------------|
| 1.1 KMS down on upload | Abort before chunks; 503 |
| 1.3 Store write fails after N chunks | Delete written objects + KMS key; FAILED/rollback |
| 1.7 Orphan `UPLOADING` | **Not this branch** (`sweep_orphaned_documents`) |
| 1.8 Empty file | 400 |
| 1.9 Magic vs extension | Magic wins; reject if not allowlisted |
| 1.10 Duplicate file | Two documents |
| 5.1 Over 500 MB | 413/400 before buffering whole body |
| 5.5 / 5.6 Filename unicode / `../` | Sanitize; never use raw name as storage path |

Download-only rows (1.2, 1.4–1.6, 3.1) are out of scope.

---

## Assumptions

- JWT + `require_roles` work enough to protect the route (or tests inject identity).
- `case_service.get_case_for_user` exists or is mocked; this branch does not implement cases.
- `audit_service.record` can be called; if audit is stubbed in tests, assert the call.
- Local chunk store and file KMS dirs are gitignored (`./data/chunks`, `./data/keys`).
- OCR is **not** run on this branch (`ocr_plan.md` wires after chunks on a later feature).
- MIME list follows `SECURITY.md` / design (wav, no `audio/mpeg` from the older plan list).

---

## Review

1. **Security holes?** Remaining: no malware scanner (not in repo). Magic bytes are the specified type check. Closed-case and 404 scoping depend on `get_case_for_user` being correct. KMS wrap must not use `SECRET_KEY`. SFTP unimplemented — local backend only, as specified for prototype ingest.

2. **Contradictions?** Chunked plan still says MinIO `{doc_id}/chunk_i` and Vault; models + ARCHITECTURE + TODO say opaque keys + file KMS — **this spec follows the latter**. Plan download uses 403; upload uses CLAUDE 404 for case-scoped miss. Plan MIME includes `audio/mpeg`; SECURITY.md / UI do not — **SECURITY.md**. `DOCUMENT_UPLOAD_FAILED` appears in the audit plan narrative but not in `AuditEventType` — **do not add it**. API.md omits 503; EDGE_CASES 1.1 requires it.

3. **Simpler design?** Single-blob encrypt is forbidden by the plan (RAM + one-key blast radius). Skipping the React component would still meet P0 API; P1 uploader is in TODO and the design map, so it stays in the file list but unmounted.

4. **EDGE_CASES?** Upload rows above are handled except 1.7 (deferred) and 5.2 (Nginx/Gunicorn timeouts — prototype runs Flask locally).

5. **Break existing features?** Registering one blueprint should not affect auth routes. New migration is additive. `create_all` in tests will also build `cases` from the Case model. Risk: `flask db upgrade` without a `cases` table fails — case-management must land first or tests use `create_all`. Do not change auth/user files.

---

## Later (not this branch)

Download / pre-verify, `GET /cases/{id}/documents`, preview, soft-delete, OCR-on-upload, SFTP backend, `sweep_orphaned_documents`, CaseDetailPage mount, MinIO/Vault.
