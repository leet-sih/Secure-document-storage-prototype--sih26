# OCR Integration Spec

## What it does
Wires the existing `app.core.ocr` engine into the document upload flow for both case documents and personal vault documents. Adds an opt-in **Auto-OCR** checkbox on upload. Each OCR-able file (image or scanned PDF) shows an inline OCR status badge and action buttons. Raw OCR text is held pending user approval; on approval it is formatted by a local LLM (Ollama / orca-mini) before being stored as `search_text`.

## User flow

### Auto-OCR checked on upload
1. File uploads; encrypt-first guarantee unchanged.
2. OCR runs inline (post-commit, best-effort).
3. Confidence < 60 % → `ocr_status = FAILED`; tile shows red "OCR Failed (XX%)".
4. Confidence ≥ 60 % → raw text saved to `ocr_raw_text`, `ocr_status = AWAITING_APPROVAL`; tile shows amber "Review OCR".

### Manual "Generate OCR" button
Shown on each row where `ocr_status = NOT_APPLICABLE` and the file is OCR-able (image/PDF).  Clicking triggers `POST /documents/<id>/ocr`; same confidence gate as above.

### Review / approve
Clicking "Review OCR" opens `OcrApprovalModal`. Modal shows raw OCR text.
- **Approve & Format** → `POST /documents/<id>/ocr/approve` → backend calls LLM formatter → stores result in `search_text`, sets `ocr_status = DONE`.
- **Dismiss** → sets `ocr_status = FAILED`.

### View OCR
When `ocr_status = DONE`, a "View OCR" button shows the formatted `search_text`.

## Files to create / modify

| File | Change |
|------|--------|
| `app/models/document.py` | add `ocr_raw_text` column |
| `app/schemas/document_schemas.py` | expose OCR fields; add `auto_ocr` to upload schema |
| `app/core/llm_formatter.py` | NEW — Ollama formatting helper |
| `app/services/document_service.py` | wire OCR hook; add `generate_ocr_for_document`, `approve_ocr` |
| `app/blueprints/documents.py` | `auto_ocr` form field; `POST /documents/<id>/ocr`; `POST /documents/<id>/ocr/approve` |
| `migrations/versions/005_ocr_approval.py` | NEW — add `ocr_raw_text` column |
| `src/types/index.ts` | add OCR fields to `DocumentMeta` |
| `src/lib/documentApi.ts` | add `generateOcr`, `approveOcr`, `dismissOcr`, update `toDocumentMeta` |
| `src/components/DocumentUploader.tsx` | Auto-OCR checkbox |
| `src/components/OcrApprovalModal.tsx` | NEW — review + approve/dismiss modal |
| `src/pages/CaseDetailPage.tsx` | OCR column in doc table |
| `src/pages/PersonalVaultPage.tsx` | OCR column in doc table |

## API contract

### Upload (modified)
`POST /cases/<id>/documents` and `POST /me/documents`
- New form field: `auto_ocr` (optional, `"1"` / `"true"` / `"false"`, default false)

### Generate OCR
`POST /documents/<id>/ocr`
- Auth: any member of the document's case, or owner of personal doc
- Request: empty body
- Response 200: `DocumentMetadataSchema` (updated)
- Errors: 404 not found/no access; 409 already done/awaiting

### Approve OCR
`POST /documents/<id>/ocr/approve`
- Auth: same
- Request: `{ "action": "approve" | "dismiss" }`
- Response 200: `DocumentMetadataSchema` (updated)
- Errors: 404; 409 if `ocr_status != AWAITING_APPROVAL`

## Security threat model
- OCR text is derived from the plaintext; it is not the plaintext itself. Storing it in Postgres is acceptable — it is search-indexed text, not the original evidence file.
- The approve endpoint requires the user to be a case member (or owner), matching the download permission model.
- LLM formatter is local-only (Ollama); `OCR_ALLOW_NETWORK=false` already enforced. Formatter falls back silently to raw text if Ollama is unreachable — it must never block approval.
- `ocr_raw_text` is cleared after approval (set to NULL) so only the formatted version persists.

## Edge cases
- Non-OCR-able files (video, audio, docx): `auto_ocr` ignored; `ocr_status = NOT_APPLICABLE`.
- Born-digital PDFs: text layer extracted directly; `ocr_status = NOT_APPLICABLE` (or `DONE` with no approval needed since no Tesseract ran).
- OCR engine not installed: `ocr_status = FAILED`, detail message explains.
- Ollama not running at approve time: formatter returns raw text unchanged; approval still succeeds.
- Repeated "Generate OCR" clicks: 409 if already `AWAITING_APPROVAL` or `DONE`.

## Review
1. **Security holes?** No — text fields in Postgres, not file content. Access checked same as download.
2. **Contradicts CLAUDE.md?** No — encrypt-first intact; OCR always post-commit.
3. **Simpler design?** Could skip the approval step, but the brief explicitly requires it.
4. **EDGE_CASES.md?** OCR failure must never fail upload — ✓ (already the guarantee).
5. **Breaks existing feature?** Download unchanged. Metadata schema additive (new nullable fields). Upload schema change is backward-compatible (auto_ocr defaults to false).
