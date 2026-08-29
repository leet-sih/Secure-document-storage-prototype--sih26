# Spec: Chunked Document Encryption + Postgres Key Storage

**Feature owner:** Rjav · **Branch:** `Rjav-document-security`
**Status:** Implemented on `Rjav-document-security` (all listed files). Two shared-bootstrap
integration steps remain out of scope — see §7 items 1 & 5.
**Parent plan:** `feature_plans/chunked_document_storage_plan.md` (source of truth)
**Related docs:** `docs/SECURITY.md`, `docs/EDGE_CASES.md` §1 & §5, `docs/ARCHITECTURE.md`

---

## 1. What this feature does and why

This implements the core of the vault: **encrypt a document into per-chunk AES-256-GCM
ciphertext on upload, and reconstruct + decrypt it on download** — exactly the pipeline in
`chunked_document_storage_plan.md`. It fills in the scaffolded (`NotImplementedError`) crypto
path end to end so a case officer can upload a file and an authorised case member can download
the byte-identical original, with tamper-evidence at every layer.

**The one deliberate deviation from the parent plan:** the parent plan stores each document's
32-byte **master key** in a local *file* KMS (`KMS_DIR/{doc}.key`). Per the product owner's
decision, this feature stores the master key **in PostgreSQL instead** — but **wrapped**
(AES-256-GCM encrypted) under `KMS_WRAPPING_KEY`, never in plaintext. See §5 for the threat
analysis of that change. Everything else follows the parent plan unchanged.

### Decisions locked with the product owner (2026-08-28)
1. **Encryption happens on the backend at upload.** Browser sends plaintext over TLS; the
   backend chunks, encrypts, and stores. (No browser-side encryption.)
2. **Decryption happens on the backend at download.** The server reconstructs plaintext in
   memory for the *one* authorised request and streams it over TLS. **No frontend decryption,
   no key material ever leaves the server.** (An earlier idea to decrypt in the browser was
   dropped — it does not hide plaintext from authorised users and only moves the key onto the
   wire; server-side decrypt is simpler and keeps keys server-only.)
3. **Master key stored in Postgres, wrapped under `KMS_WRAPPING_KEY`.** The file KMS is
   replaced by a DB-backed keystore behind the *same* `kms.py` function signatures, so
   `document_service` is agnostic to where keys live.

### File types covered — encryption is type-agnostic
The chunked encryption operates on the **raw bytes of the file**, so it is identical for every
allowed type — there is nothing text-specific about it. A `.txt`, a `.pdf`, a scanned
JPEG/PNG/TIFF, a `.docx`/`.xlsx`, an `.mp4`, or an audio file are all split into 1 MB chunks and
AES-256-GCM encrypted the same way. **The whole file is always encrypted at rest regardless of
its type or contents.** `ALLOWED_MIME_TYPES` (from the parent plan) already includes PDF, DOCX,
XLSX, JPEG, PNG, TIFF, MP4, MPEG-audio and WAV — no per-type branch exists in the crypto path.

### Encrypt-first, OCR-best-effort (the guarantee)
OCR/text-extraction (its own plan, `ocr_plan.md`) is the layer that makes a **PDF or image**
*searchable*; it does **not** change how the file is stored. This spec guarantees the ordering
and independence:
1. **Mandatory:** validate → chunk → encrypt → store chunks → store wrapped key → compute
   integrity hash → commit `Document` as `ACTIVE`. The whole file is now encrypted, whatever its
   type. This step must fully succeed for the upload to return `201`.
2. **Best-effort, after commit:** inline OCR (per `ocr_plan.md`) may then run on the in-memory
   plaintext to populate `search_text` / `ocr_*`. **If OCR is uncertain, unavailable, times out,
   or fails, the document stays `ACTIVE` and fully encrypted** — only `ocr_status` reflects it
   (`LOW_CONFIDENCE` / `FAILED` / `NOT_APPLICABLE`) and `search_text` is left empty. **OCR failure
   never fails the upload and never affects whether/how the file is encrypted.** No decrypted file
   is ever written to disk during OCR — in-memory only.

This spec implements step 1 and the `reconstruct_bytes()` plaintext hook OCR consumes; the OCR
engine itself stays in `ocr_plan.md`'s scope. `document_service.upload_document` must commit the
`ACTIVE` document **before** invoking OCR, and wrap the OCR call so any exception is caught,
logged, and turned into an `ocr_status` — it must not propagate to the upload response.

### Explicitly OUT of scope for this spec
- Frontend components (`DocumentUploader`, `DocumentList`, etc.) — backend + API only.
- `GET /documents/{id}/preview` (P1) and `PATCH /documents/{id}` (metadata edit) — adjacent
  routes, not part of the crypto/keystore path.
- SFTP chunk-store backend (Server B) — the `_*_sftp` functions stay `NotImplementedError`;
  this spec implements only the `local` backend. `CHUNK_STORE_BACKEND=local`.
- OCR **engine/pipeline** implementation (Tesseract, image preprocessing, confidence scoring,
  language packs) — lives in `ocr_plan.md`. This spec only guarantees the **encrypt-first
  ordering** described above and exposes the `reconstruct_bytes()` plaintext hook OCR calls. The
  guarantee that "the whole file gets encrypted regardless of OCR" **is** in scope; the OCR code
  is not.

---

## 2. Exact files created / modified (no others)

**Created**
| File | Purpose |
|------|---------|
| `feature_plans/specs/document_encryption_keystore_spec.md` | This spec |
| `codebase/backend/app/models/document_key.py` | New `DocumentKey` model — wrapped master key row |
| `codebase/backend/migrations/versions/<hash>_document_keys.py` | Alembic migration for the `document_keys` table (autogenerated) |

**Modified**
| File | Change |
|------|--------|
| `codebase/backend/app/core/crypto.py` | Add `wrap_master_key()` / `unwrap_master_key()` (AES-256-GCM under the wrapping key). Existing functions untouched. |
| `codebase/backend/app/core/kms.py` | Implement `store_key` / `get_key` / `delete_key` against Postgres (wrapped). **Signatures unchanged.** Update module docstring (file→DB). |
| `codebase/backend/app/storage/chunk_store.py` | Implement `_local_path`, `_put_local`, `_get_local`, `_delete_local`. SFTP stays TODO. |
| `codebase/backend/app/services/document_service.py` | Implement `upload_document`, `download_document`, `reconstruct_bytes`, `soft_delete`, `list_documents`. Commit the `ACTIVE` document **before** any (best-effort, exception-swallowed) OCR call — OCR must never fail the upload. |
| `codebase/backend/app/blueprints/documents.py` | Implement `POST /cases/{id}/documents`, `GET /cases/{id}/documents`, `GET /documents/{id}/download`, `DELETE /documents/{id}`. |
| `codebase/backend/app/models/__init__.py` | Add one import line so Flask-Migrate discovers `DocumentKey`. |

**NOT touched** (confirmed unnecessary): `config.py` (`KMS_WRAPPING_KEY`, `CHUNK_STORAGE_DIR`,
`CHUNK_STORE_BACKEND`, `MAX_CONTENT_LENGTH`, `CHUNK_SIZE_BYTES` all already present),
`requirements.txt` (`python-magic`, `cryptography` already present), `document_schemas.py`
(existing `DocumentUploadSchema` / `DocumentMetadataSchema` already sufficient).

**Dependency on other work:** `document_service` calls `case_service.get_case_for_user()` /
`user_has_access()` and `audit_service.record()`. `audit_service` is implemented; `case_service`
is still `NotImplementedError`. Download/list will not function end-to-end until `case_service`
lands. This is noted, not fixed here (out of scope — see Minimal File Footprint rule).

---

## 3. Data model changes

### New table: `document_keys`
One row per document, holding the **wrapped** master key. Separate table (not a column on
`documents`) so key material is isolated from metadata and can move to Vault later without
touching the metadata schema.

```
document_keys
├── document_id     UUID  PK, FK -> documents(id) ON DELETE RESTRICT
├── wrapped_key_hex TEXT  NOT NULL   -- hex of AES-256-GCM(master_key) incl. 16-byte tag (48 bytes -> 96 hex chars)
├── wrap_iv_hex     TEXT  NOT NULL   -- hex of the 12-byte GCM nonce used for wrapping (24 chars)
└── created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
```

- `document_id` is the **primary key** (exactly one key per document; enforces 1:1).
- Stored as hex `TEXT` to match house style (`document_chunks.iv_hex`, `chunk_hash`).
- **Never** stores the plaintext master key. **Never** stores `KMS_WRAPPING_KEY`.
- No `list`-style query is ever run against this table by application code (mirrors the Vault
  "no list capability" rule) — access is always by known `document_id`.

`documents` and `document_chunks` are **unchanged** (already defined; this spec adds no columns
to them).

### Migration note
No Alembic version files exist yet in the repo (only `migrations/README.md`). The
`document_keys` table will be picked up by `flask db migrate` alongside the other models when
the initial schema migration is generated. If the initial migration already exists by
implementation time, add a dedicated migration for `document_keys` only. **Open item — see §7.**

---

## 4. API contract

Prefix: `/api/v1`. All routes require a valid JWT (`@jwt_required`). Roles via
`require_roles(...)`. Case-scoped resources return **404 (not 403)** to non-members.

### 4.1 `POST /cases/{case_id}/documents` — upload
- **Roles:** `SUPER_ADMIN`, `CASE_OFFICER`. Rate-limited (`UPLOAD_LIMITS`).
- **Body:** `multipart/form-data`
  - `file` — binary (streamed via `request.stream`; never `request.get_data()`)
  - `doc_type` — one of `DOC_TYPES` (validated by `DocumentUploadSchema`)
  - `title` — optional, ≤255
  - `tags` — optional, ≤10 × `^[a-z0-9\-]{1,50}$`
- **Success:** `201` + `DocumentMetadataSchema` (metadata only — never IVs, hashes, chunk info).
- **Errors:**
  | Code | When |
  |------|------|
  | `400 VALIDATION_ERROR` | missing/invalid form fields, empty (0-byte) file |
  | `400 UNSUPPORTED_MEDIA_TYPE` | magic-byte MIME ∉ `ALLOWED_MIME_TYPES` |
  | `404` | `case_id` not visible to caller (non-member) |
  | `409 CASE_NOT_OPEN` | case is `CLOSED`/`ARCHIVED` |
  | `413 PAYLOAD_TOO_LARGE` | exceeds `MAX_CONTENT_LENGTH` (500 MB) |
  | `500` | encryption/storage failure (after full rollback + cleanup) |
- **Audit:** `DOCUMENT_UPLOADED` (metadata: filename, size_bytes, chunks). Never logs content.

### 4.2 `GET /cases/{case_id}/documents` — list
- **Roles:** any case member.
- **Success:** `200` + `[DocumentMetadataSchema]`, excludes `is_deleted=True`.
- **Errors:** `404` if case not visible to caller.

### 4.3 `GET /documents/{document_id}/download` — reconstruct + stream plaintext
- **Roles:** any member of the document's case.
- **Behaviour:** **pre-verify every chunk** (SHA-256 == `chunk_hash`, GCM tag valid, overall
  `integrity_hash` matches) **before yielding a single byte**, then stream decrypted plaintext.
- **Success:** `200`, `Content-Disposition: attachment; filename="<sanitized>"`,
  `Content-Type: <mime_type>`, `X-Content-Type-Options: nosniff`.
- **Errors:**
  | Code | When |
  |------|------|
  | `404` | document deleted or case not visible to caller |
  | `422 INTEGRITY_VIOLATION` | any chunk hash mismatch / GCM `InvalidTag` / integrity-hash mismatch / chunk count mismatch |
  | `503` | keystore unreachable / master key missing (never serve a partial/undecryptable file) |
- **Audit:** `DOCUMENT_DOWNLOADED` on success; `INTEGRITY_VIOLATION` on tamper detection;
  `UNAUTHORIZED_ACCESS_ATTEMPT` is implicit via the 404 path (no separate event needed).

### 4.4 `DELETE /documents/{document_id}` — soft delete
- **Roles:** `SUPER_ADMIN`, `CASE_OFFICER` (of that case).
- **Behaviour:** sets `is_deleted=True`, `deleted_by`, `deleted_at`. **Chunks, keys, and rows
  remain** (legal retention). No physical deletion.
- **Success:** `204`. **Errors:** `404` if not visible.
- **Audit:** `DOCUMENT_DELETED`.

---

## 5. Security threat model

### 5.1 Crypto design (unchanged from parent plan)
- Per-chunk key = `HKDF-SHA256(master_key, salt=document_id, info="chunk-{i}")` — already in
  `crypto.derive_chunk_key`. One key encrypts exactly one chunk ⇒ random 96-bit GCM IV can
  never collide under a key ⇒ nonce-reuse failure is structurally impossible.
- `chunk_hash = SHA256(ciphertext incl. tag)`; `integrity_hash = SHA256(concat chunk_hashes)`.
- Opaque storage keys (`secrets.token_hex(16)`) — chunk store reveals no doc/order structure.

### 5.2 Master-key wrapping (the new part)
- `master_key` (32 random bytes, `crypto.generate_master_key`) is wrapped with
  `AES-256-GCM(KMS_WRAPPING_KEY, iv=os.urandom(12), master_key)` and only the **wrapped** form
  (+ its IV) is written to `document_keys`. Unwrap on download.
- `KMS_WRAPPING_KEY` lives in the **environment**, is **distinct from `SECRET_KEY` and
  `JWT_SECRET`**, and is **never** written to the DB, logs, or chunk store.
- Each master key is wrapped once with its own random 12-byte IV. Total wraps ≪ 2³², so random
  IVs under the single shared wrapping key stay collision-safe.
- Raw wrap/unwrap AES calls live **only** in `crypto.py` (per CLAUDE.md). `kms.py` orchestrates
  (derive nothing, just wrap→store / fetch→unwrap).

### 5.3 Who can call what, and abuse mitigation
| Actor | Capability | Mitigation |
|-------|-----------|------------|
| Non-member | none | 404 (not 403) on all case-scoped routes — existence not confirmed |
| `INVESTIGATOR`/`PROSECUTOR`/`AUDITOR`/`VIEWER` | download/list only if case member; no upload/delete | `require_roles` + `case_service` membership check |
| `CASE_OFFICER` | upload/delete in own cases | role gate + membership check |
| DB-read attacker | sees wrapped keys + opaque chunk metadata | **useless without** `KMS_WRAPPING_KEY` (env) **and** the chunk ciphertext (chunk store) |
| Chunk-store attacker (Server B) | flat opaque ciphertext blobs | no keys, no structure, no metadata |
| Attacker with wrapping key alone | can unwrap keys | but has no ciphertext and no metadata |

### 5.4 Honest note on the Postgres-keystore change (deviation from parent plan)
The parent plan keeps keys in a **separate file store** so that "a stolen database is useless."
Moving wrapped keys **into** the database means a DB dump now contains *both* chunk metadata
*and* wrapped keys in one place. **The "stolen DB is useless" property still holds**, because:
1. the wrapping key is in the environment, not the DB, and
2. the actual ciphertext is in the chunk store, not the DB.
An attacker still needs **two of three** compromised: {DB + app-host env} **and** {chunk store}.
This is compliant with CLAUDE.md's rule — *"Do not store master keys … in the DB in plaintext
(Vault/KMS or **app-encrypted** only)"* — because the key is app-encrypted. Residual risk
(accepted for the prototype): a full app-host compromise yields DB **and** `KMS_WRAPPING_KEY`
together, then only the chunk store stands between the attacker and plaintext. Documented, and
the `kms.py` interface is unchanged so a Vault swap later restores full separation.

### 5.5 Other controls
- MIME verified by **magic bytes** (`python-magic`) on the first 2048 bytes, not the client
  header or extension.
- Filename sanitised to `[a-zA-Z0-9._-]`, ≤255; `original_filename` kept separately.
- Streamed upload (`request.stream`) — never buffer 500 MB via `request.get_data()`.
- No document content or PII in logs — only IDs, sizes, counts, event types (`structlog`).
- `MAX_CONTENT_LENGTH` enforced by Flask; empty files rejected at validation.

---

## 6. Edge cases (cross-ref `docs/EDGE_CASES.md` §1 & §5, parent plan table)

| Scenario | Behaviour |
|----------|-----------|
| Keystore row missing / unreadable on download | `503`; never serve an undecryptable file |
| Chunk-store write fails mid-upload | Roll back: `delete_chunks(written)` + `kms.delete_key` + `db.rollback`, mark `FAILED`. No orphans. |
| Wrap succeeds, chunk write fails | Same rollback; `document_keys` row is inside the same DB transaction ⇒ rolled back atomically |
| Ciphertext modified in chunk store | `SHA256 != chunk_hash` **or** GCM `InvalidTag` ⇒ `422` before any byte streamed |
| Chunk rows reordered / index tampered | Overall `integrity_hash` mismatch ⇒ `422` |
| `total_chunks` ≠ rows found | `422` (incomplete document) |
| Empty (0-byte) file | Rejected at validation (min 1 byte / 0 chunks invalid) |
| `.pdf` that is really an `.exe` | Magic-byte check rejects (`400`) |
| Non-text file (PDF, image, video, audio, office doc) | Encrypted byte-for-byte identically to any other file — no type-specific path in the crypto pipeline |
| OCR uncertain / fails / times out / >50 pages | Document stays `ACTIVE` and **fully encrypted**; `ocr_status=LOW_CONFIDENCE`/`FAILED`, `search_text` empty. Upload still returns `201`. Encryption never depends on OCR. |
| Client disconnects mid-upload | Doc stuck `UPLOADING`; on-demand `tasks/maintenance.py` sweep purges (chunks + key + rows). No Celery in prototype. |
| Access token expires mid-download | Auth checked once at request start; long transfer completes |
| Soft-deleted doc download | `404` |

**Atomicity choice:** the `document_keys` row is inserted in the **same DB session/transaction**
as `documents` + `document_chunks`, so a failed upload cannot leave an orphaned key (a genuine
advantage of the Postgres keystore over the file KMS). The chunk-store writes are the only
non-transactional side effect and are explicitly cleaned up on failure.

---

## 7. Open questions / assumptions
1. **Initial migration ownership.** No Alembic versions exist yet. Assumption: this feature
   adds the `DocumentKey` model + import; the table is realised either in the project's initial
   `flask db migrate` or a dedicated migration if the baseline already exists. Confirm who owns
   the baseline migration before running.
2. **`case_service` not yet implemented.** Download/list/delete need `get_case_for_user` /
   `user_has_access`. Implemented against those signatures; end-to-end works once `case_service`
   lands. Not fixed here (out of scope).
3. **Pre-verification buffers the whole document in RAM** on download (parent-plan choice for
   the prototype). Acceptable at prototype file sizes; two-pass streaming is a production TODO.
4. Assumption: `require_roles`, `Role`, `UPLOAD_LIMITS`, and the `errors.py` error envelope
   already exist and are used as-is (confirmed present in `core/`).
5. **Shared-bootstrap integration NOT done here (out of scope, flagged for the app-wiring owner):**
   - `app/__init__.py::_register_blueprints` is still a `pass` stub — the `documents_bp` is
     implemented and ready but **not yet registered**, so routes aren't reachable until the
     shared app factory is wired. Adding only this blueprint to the collective stub would
     pre-empt the coordinated wiring of all blueprints, so it's intentionally left.
   - `errors.py::register_error_handlers` / `app/__init__.py::_register_error_handlers` are
     stubs, so raised `APIError`/`IntegrityError` won't render as the JSON envelope (they'll be
     generic 500s) until that shared work lands. The blueprint/service raise the *correct*
     status/code per §4; only the rendering is pending.

### Implementation notes (decisions made while coding)
- **Audit call site:** `services/__init__.py` mandates that normal-action audit events are
  recorded in the **blueprint** layer, not the service. So `DOCUMENT_UPLOADED` / `DOWNLOADED` /
  `DELETED` are recorded in `documents.py`; only the security event `INTEGRITY_VIOLATION` is
  recorded inside `document_service` (the allowed exception), where tampering is detected.
  `soft_delete` returns the `Document` so the blueprint can audit it.
- **`text/plain` added** to `ALLOWED_MIME_TYPES` (beyond the parent plan's list) so plain-text
  documents can be uploaded — matches the product owner's "text now" note. All other allowed
  types come straight from the parent plan.
- **Atomic writes** in the local chunk store (temp file + `os.replace`) so a crash mid-write
  can't leave a partial chunk that would later fail its hash check.
- **Verified locally:** crypto wrap/unwrap round-trip, wrong-key rejection, per-chunk key
  determinism/independence, AES-GCM tamper detection, and integrity-hash ordering sensitivity
  all pass (`crypto.py` has no Flask/DB deps). Full app import + a running DB are needed to
  exercise the service/blueprint end-to-end.

---

## Review

**1. Are there any security holes in this design?**
- The main new surface is the Postgres keystore. Mitigated by app-encryption (wrapping key in
  env, distinct from other secrets) — a DB dump yields only wrapped keys. Residual risk (host
  compromise = DB + wrapping key together) is documented and bounded by the separate chunk
  store. No plaintext key ever hits DB/logs/chunk store.
- Wrap uses AES-256-GCM with a random per-key IV under a shared key; wrap count ≪ 2³² keeps
  random-IV collision risk negligible. All raw crypto stays in `crypto.py`.
- Download pre-verifies integrity **before** streaming, so no partial/tampered bytes reach the
  client. Case access is re-checked per request; 404 (not 403) avoids existence disclosure.
- No hole introduced in the audit chain (uses existing `audit_service`, advisory-locked).

**2. Does anything contradict CLAUDE.md / SECURITY.md / the parent plan?**
- **Deviation, not contradiction:** keys move from file KMS → Postgres. CLAUDE.md permits DB
  storage when *app-encrypted*; this wraps under `KMS_WRAPPING_KEY`, so it complies. Documented
  explicitly in §1 and §5.4. `kms.py` signatures are preserved so no caller changes and a Vault
  swap remains a drop-in. All other rules (per-chunk keys, no key reuse, no plaintext on disk,
  parameterized queries via ORM, marshmallow `unknown=RAISE`, magic-byte MIME, no PII in logs)
  are upheld.

**3. Is there a simpler design meeting the same requirements?**
- Considered storing the wrapped key as a **column on `documents`** (fewer tables). Rejected:
  a separate `document_keys` table isolates key material, keeps the metadata schema stable for
  the eventual Vault swap, and mirrors the "no list of keys" rule. The 1:1 PK keeps it simple.
- Considered keeping the file KMS. Rejected per product-owner decision; Postgres also gives
  transactional cleanup of the key on failed upload (a real simplification of the failure path).

**4. Which `docs/EDGE_CASES.md` cases apply and are they handled?**
- §1 (chunk integrity/tamper) and §5 (upload failure / orphan cleanup) — both covered in §6:
  hash + GCM + integrity-hash pre-verification, atomic DB rollback + chunk cleanup on failure,
  and the on-demand maintenance sweep for stuck `UPLOADING` docs.

**5. Could this break any existing feature? Risks + mitigation.**
- The feature only *implements* currently-`NotImplementedError` stubs, so it cannot regress
  working behaviour. Risk: `kms.py` docstring/config still describe a file KMS — mitigated by
  updating the `kms.py` docstring and noting `KMS_DIR` becomes unused (left in config,
  untouched, to avoid shared-config churn per Minimal File Footprint).
- Risk: signatures feature (`document_signature.py`) signs `integrity_hash` — unaffected, since
  `integrity_hash` computation is unchanged from the parent plan.
- Risk: OCR/search will need server-side plaintext — provided via `reconstruct_bytes()`, which
  they can call; no coupling introduced now. The **encrypt-first, OCR-best-effort** guarantee
  (§1) ensures the whole file is always encrypted for **any** file type (PDF, image, video,
  audio, office, text) and that an unsure/failed OCR run cannot fail the upload or leave a file
  unencrypted — it only affects `ocr_status`/`search_text`.
