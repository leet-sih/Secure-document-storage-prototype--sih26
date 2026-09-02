# Spec: File viewer (metadata panel + server-side preview)

Sources: `CLAUDE.md` (design map, 404-not-403, crypto only in `crypto.py`), `docs/API.md` preview, `feature_plans/chunked_document_storage_plan.md` reconstruct + pre-verify, `docs/EDGE_CASES.md` §1 and §3.1, `feature_plans/audit_trail_plan.md` (`DOCUMENT_PREVIEWED`), `design/github.md` → `DocumentDetailPanel`, `codebase/frontend/FRONTEND_DESIGN_CONTEXT.md` §6.5 / §7.6. Prototype storage: local chunk store + file KMS (not MinIO/Vault).

This branch is **view only**. Do not implement download streaming, list, upload, delete, sign, share, OCR, SFTP, or `CaseDetailPage`.

---

## What and why

An officer who can access a case opens a document and sees its metadata plus an in-app preview. Ciphertext is reconstructed in memory, integrity is checked **before** any preview payload is produced, and the client never receives the original file bytes (no PDF/DOCX/JPEG blob for `<iframe>` / `<img src=blob>` of the evidence file). Images and PDFs are re-encoded as PNG pages. `text/plain` is returned as JSON text for a React text node (`<pre>`), never as `text/html`.

User-facing: `DocumentDetailPanel` slides in from the right (400px; full overlay on small screens). Close with X or Escape. Preview area under the metadata. Download / Sign / Share buttons are **visible to match the prototype but disabled** (those features are other branches).

Unmounted until `CaseDetailPage` exists (same pattern as `DocumentUploader`).

---

## Exact files

No other files.

**Create**

| Path | Why |
|------|-----|
| `feature_plans/specs/file_viewer_spec.md` | This spec |
| `codebase/backend/tests/documents/test_preview.py` | Reconstruct + preview + 404/422 |
| `codebase/frontend/src/components/DocumentDetailPanel.tsx` | Design map |
| `codebase/frontend/src/hooks/useDocumentPreview.ts` | Fetch metadata + preview (README: components should not own `apiFetch`) |

**Modify**

| Path | Why |
|------|-----|
| `codebase/backend/app/services/document_service.py` | `reconstruct` (internal) + `preview_document` + `get_document_for_user`. Leave `download_document` / list / delete as `NotImplementedError` |
| `codebase/backend/app/blueprints/documents.py` | `GET /documents/<id>` and `GET /documents/<id>/preview` only |
| `codebase/backend/app/schemas/document_schemas.py` | `DocumentPreviewSchema` dump |
| `codebase/backend/requirements.txt` | `pymupdf` (PDF→PNG, no Poppler). `Pillow` for image re-encode (explicit; also used via `qrcode[pil]`) |
| `codebase/frontend/src/types/index.ts` | Preview JSON shape |
| `codebase/frontend/src/components/README.md` | Register `DocumentDetailPanel` |
| `docs/API.md` | Preview is JSON (PNG pages and/or text), not a raw PNG stream |

**Do not modify:** upload path, MIME allowlist, `kms.py`, `crypto.py` (only call existing decrypt/HKDF/hash), `chunk_store.py`, models, migrations, `App.tsx`, `CaseDetailPage`, `DocumentUploader`, `SECURITY.md` allowlist.

---

## Data model

None. Reads `documents` + `document_chunks`. Never serializes `integrity_hash`, IVs, `storage_key`, or chunk hashes.

---

## API

### GET `/api/v1/documents/{document_id}`

Authorization: Bearer. Roles: `SUPER_ADMIN`, `CASE_OFFICER`, `INVESTIGATOR`, `PROSECUTOR` (`@require_roles`). `AUDITOR` / `VIEWER` → 403 (system role).

Load document; if missing, `is_deleted`, or `status != ACTIVE` → **404**. Then `get_case_for_user(case_id, caller)` — miss → **404** (never 403 for the wrong case). CLOSED cases may still preview (read-only).

**200:** `DocumentMetadataSchema` (existing dump). Rate limit: `DEFAULT_LIMITS`.

### GET `/api/v1/documents/{document_id}/preview`

Same auth and 404 rules. Rate limit: `DEFAULT_LIMITS`.

**Processing:**

1. Access as above.
2. If `mime_type` not in `{application/pdf, image/jpeg, image/png, image/tiff, text/plain}` → **400** `VALIDATION_ERROR` “Preview is not available for this file type”.
3. Load chunks by `chunk_index`. Count mismatch, missing object, ciphertext hash mismatch, GCM `InvalidTag`, or `integrity_hash` mismatch → **422** `INTEGRITY_VIOLATION`, audit `INTEGRITY_VIOLATION`. **Zero preview fields** in the body.
4. KMS missing/unreadable → **503** `KMS_UNAVAILABLE`. No partial decrypt to the client.
5. Decrypt only in RAM. Never write plaintext to disk.
6. Render:
   - PDF: PyMuPDF pixmap PNG, max **20** pages.
   - JPEG/PNG/TIFF: Pillow convert RGB (or RGBA→RGB on white), PNG; TIFF frames capped at 20.
   - `text/plain`: UTF-8 (`errors=replace`), strip NUL, max **524288** characters; `truncated` if cut. Frontend must put this in a text node, never `dangerouslySetInnerHTML`.
7. `audit_service.record(DOCUMENT_PREVIEWED)` with filename, mime_type, page_count — no content.

**200** `DocumentPreviewSchema`:

```json
{
  "document_id": "uuid",
  "mode": "pages",
  "pages_png_base64": ["iVBOR..."],
  "text": null,
  "page_count": 1,
  "truncated": false
}
```

`mode` is `"text"` for `text/plain` (`pages_png_base64` empty, `text` set). Original file bytes are never a response `Content-Type`.

---

## Frontend

`useDocumentPreview(documentId)` → `{ meta, preview, loading, error, reload }`. Calls the two GETs. Does not keep preview in a module-level cache. Unmount / `documentId` change drops state.

`DocumentDetailPanel`: props `documentId`, `onClose`. Tokens from `CLAUDE.md`. Metadata block from design (filename, type, size, chunks, status, tags, uploaded_by UUID, created_at). Preview: `<img>` from `data:image/png;base64,...` or `<pre>` for text. Unsupported / 400 / 422 / 503: error banner, no images. Loading: spinner text with `Loader` not required if lucide is not a dependency — use the same muted copy pattern as `DocumentUploader` (no new npm packages).

**Design gap:** the prototype panel has no page canvas. This spec adds a preview region **below** metadata so `GET /preview` has a UI. Download/Sign/Share remain in the footer but `disabled`.

No `console.log` of content. No lucide (`package.json` has none).

---

## Security

| Threat | Mitigation |
|--------|------------|
| Probe another case’s document id | 404 via case membership |
| XSS via PDF/HTML | No original bytes; PNG or JSON text in `<pre>` |
| XSS via text preview | JSON string + React text node; strip NUL |
| Tampered chunk | Pre-verify; 422; no pages/text |
| Key/DB split failure | 503 if KMS down |
| RAM DoS on huge PDF | 20-page cap |
| Logs leak evidence | IDs, mime, page_count only |
| Client decrypt | Forbidden |

---

## Edge cases

| # | Behaviour |
|---|-----------|
| 1.2 KMS down | 503, no preview body |
| 1.4 missing chunk | 422 |
| 1.5 ciphertext changed | 422 |
| 1.6 reorder | 422 integrity_hash |
| 2.5 membership revoked | next preview 404 |
| 3.1 token at request start | N/A (JSON, not long stream) |
| DOCX/XLSX/MP4/WAV | 400, panel message |
| `text/plain` not yet uploadable on this branch | Preview still handles the MIME if a row exists |

Download-only token-mid-stream is out of scope.

---

## Assumptions

- `get_case_for_user` exists or is patched in tests (same as upload).
- `audit_service.record` may hit Postgres advisory lock; tests mock it at the blueprint or use service-level tests only for reconstruct.
- Pillow + PyMuPDF install in the backend venv.
- `text/plain` ingest may land on another branch; this branch still previews that MIME.

---

## Review

1. **Security holes?** Preview JSON still carries evidence content (PNG or text) to an authorized browser — required to view. Unauthorized callers get 404. HTML is not a preview type. 20-page cap is a DoS control, not a secrecy control. No malware scan (same as upload).

2. **Contradictions?** API.md currently says “returns PNG pages” as if `image/png` HTTP body; this spec uses JSON so `apiFetch()` can parse it and so text is not stuffed into a PNG-only response. Chunked plan download uses 403; this spec uses CLAUDE **404**. Plan reconstruct 403 on access — **404**. `integrity_hash` stays off the wire. Download remains unimplemented (other branch).

3. **Simpler design?** Sending the original JPEG as `img src` is simpler and weaker (polyglot/XSS). Single PNG HTTP body cannot carry multi-page + text. Client-side PDF.js would send raw PDF — rejected.

4. **EDGE_CASES?** §1 reconstruct rows handled. 1.7 orphan sweep not this branch. 3.1 N/A.

5. **Break existing features?** New GET routes only. Upload POST unchanged. Registering extra routes on `documents_bp` is additive. New Python deps must be pip-installed or PDF/image tests skip/fail — listed in `requirements.txt`. Frontend hook unused until case detail mounts the panel — no route change, no break.

---

## Later (not this branch)

`GET /download` attachment stream, list, CaseDetailPage mount, Sign/Share/Delete enable, OCR badge, signature list fetch.
