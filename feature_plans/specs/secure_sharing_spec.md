# Spec: Secure Sharing — document, case-documents, and full-case share links

## What the Feature Does

Allows a CASE_OFFICER or SUPER_ADMIN to generate a time-limited, email-gated share link that
lets an external party (prosecutor, court clerk, forensic expert) access evidence without a
system account. Three sharing scopes:

- **DOCUMENT** — a single document. Recipient downloads one file; integrity-verified before byte one streams.
- **CASE_DOCUMENTS** — all non-deleted documents in a case. Recipient sees the doc list + OCR metadata, then downloads individual files.
- **CASE_FULL** — complete case: metadata, members list, and all documents. Read-only window on the full case.

All three scopes share the same token security model, email gate, expiry/max-uses mechanics,
and audit trail. Every access (including case-level access) logs `SHARE_LINK_ACCESSED` to the
hash-chained audit trail.

Step-up MFA (TOTP re-verification) is required to create any share link.

---

## Exact Files Created or Modified

**New files:**
- `feature_plans/specs/secure_sharing_spec.md` — this file
- `codebase/backend/migrations/versions/009_sharing.py` — DB migration
- `codebase/frontend/src/lib/shareApi.ts` — public + authenticated share API calls
- `codebase/frontend/src/components/ShareModal.tsx` — share creation modal (all scopes)
- `codebase/frontend/src/pages/ShareAccessPage.tsx` — public share access page

**Modified files:**
- `codebase/backend/app/core/audit_events.py` — add `CASE_SHARED`
- `codebase/backend/app/models/document_share_link.py` — add `share_scope`, nullable `case_id`, make `document_id` nullable
- `codebase/backend/app/schemas/sharing_schemas.py` — add `CaseShareCreateSchema`, update `ShareInfoSchema`
- `codebase/backend/app/services/sharing_service.py` — full implementation
- `codebase/backend/app/blueprints/sharing.py` — doc + case share routes (authenticated)
- `codebase/backend/app/blueprints/share_access.py` — public access routes (no JWT)
- `codebase/backend/app/__init__.py` — register sharing blueprints
- `codebase/frontend/src/types/index.ts` — add ShareLink, ShareInfo types
- `codebase/frontend/src/App.tsx` — add `/share/:token` public route
- `codebase/frontend/src/pages/CaseDetailPage.tsx` — wire ShareModal into doc rows + add case-level share button

---

## Data Model Changes

### Extend `document_share_links`

New columns added by migration 009:

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| `share_scope` | TEXT NOT NULL | `'DOCUMENT'` | `DOCUMENT \| CASE_DOCUMENTS \| CASE_FULL` |
| `case_id` | UUID FK → cases.id | NULL | Required for CASE_* scopes; optional for DOCUMENT (case context) |

Existing column change:
- `document_id` — remove `NOT NULL` constraint (becomes nullable; required only for DOCUMENT scope)

Invariants enforced at the service layer (not DB constraints, to keep migration simple):
- `share_scope = DOCUMENT` ⟹ `document_id IS NOT NULL`
- `share_scope IN (CASE_DOCUMENTS, CASE_FULL)` ⟹ `case_id IS NOT NULL AND document_id IS NULL`

---

## API Contract

### Authenticated — document share

**POST /api/v1/documents/{id}/share** `[SUPER_ADMIN, CASE_OFFICER]` + step-up MFA

```json
// Request
{
  "expires_in_hours": 24,
  "max_uses": 3,
  "allowed_email": "prosecutor@court.gov.in",
  "note": "For bail hearing"
}
// Response 201
{
  "share_id": "uuid",
  "share_url": "http://localhost:5173/share/abc123...",
  "expires_at": "2026-09-03T14:00:00Z",
  "max_uses": 3
}
```

**GET /api/v1/documents/{id}/shares** `[SUPER_ADMIN, CASE_OFFICER]`

Returns list of share links for a document (not exhausted / revoked filtered out for readability but all returned).

**DELETE /api/v1/documents/{id}/shares/{share_id}** `[creator or SUPER_ADMIN]`

Sets `is_revoked=True`. Future access → 410.

### Authenticated — case share

**POST /api/v1/cases/{id}/share** `[SUPER_ADMIN, CASE_OFFICER]` + step-up MFA

```json
// Request
{
  "share_scope": "CASE_FULL",      // "CASE_DOCUMENTS" or "CASE_FULL"
  "expires_in_hours": 24,
  "max_uses": 1,
  "allowed_email": "judge@hc.gov.in",
  "note": "High Court review"
}
// Response 201
{
  "share_id": "uuid",
  "share_url": "http://localhost:5173/share/abc123...",
  "expires_at": "2026-09-03T14:00:00Z",
  "max_uses": 1
}
```

**GET /api/v1/cases/{id}/shares** `[SUPER_ADMIN, CASE_OFFICER]`

Lists all share links for the case (all scopes).

**DELETE /api/v1/cases/{id}/shares/{share_id}** `[creator or SUPER_ADMIN]`

### Public — share access (no JWT)

**GET /api/v1/share/{token}/info**

```json
{
  "scope": "CASE_FULL",
  "filename": null,           // set only for DOCUMENT scope
  "case_title": "State vs. Ravi",
  "case_number": "FIR-2026-DL-001",
  "doc_count": 7,             // set for CASE_* scopes
  "file_size_bytes": null,
  "expires_at": "2026-09-03T14:00:00Z",
  "requires_email": true,
  "is_valid": true
}
```
Returns 410 if expired/revoked/not-found (no info about which).

**POST /api/v1/share/{token}/download**

Body: `{"email": "..."}`

- DOCUMENT scope: Checks email gate, atomically increments `use_count`, runs full integrity verification, streams the decrypted file. Logs `SHARE_LINK_ACCESSED`.
- CASE_DOCUMENTS scope: Checks email gate, increments `use_count`, returns `{scope, case_id, case_title, documents: [{id, filename, doc_type, file_size_bytes, ocr_status, ocr_confidence, created_at}]}`. Logs `SHARE_LINK_ACCESSED`.
- CASE_FULL scope: Same as CASE_DOCUMENTS but also returns `{case: {id, case_number, title, description, status, priority, category, members, created_at}, documents: [...]}`. Logs `SHARE_LINK_ACCESSED`.

Returns 410 expired/revoked/exhausted; 403 email mismatch; 404 unknown token.

**POST /api/v1/share/{token}/file/{doc_id}**

Body: `{"email": "..."}`

CASE scope only. Re-validates token+email gate (does NOT increment `use_count`). Runs integrity check, streams the decrypted file. The document must belong to the share's case. Logs `SHARE_LINK_ACCESSED` with `{sub_download: true, doc_id}`.

Returns 400 if scope is DOCUMENT (use /download instead); 404 if doc not in case; 410/403 same as above.

---

## Security Threat Model

| Threat | Mitigation |
|--------|-----------|
| Brute-force token | `secrets.token_urlsafe(32)` = 256-bit entropy; rate limit 5/hour/IP |
| DB compromise leaks tokens | Only `SHA256(token)` stored; raw token never persisted |
| Recipient forwards URL | Email gate is named-recipient restriction, not crypto binding. UI clearly states this. Audit trail records every access with IP+UA |
| Replay after max_uses | Atomic `UPDATE ... WHERE use_count < max_uses RETURNING id` — one winner, one loser |
| Case-scope share bypasses doc-level control | Access to `case_id` verified via `case_service.get_case_for_user` at link creation. ARCHIVED case → block share creation; block access to existing links via 410 |
| Individual file download after case token exhausted | `/share/{token}/file/{doc_id}` re-validates token validity (not-expired, not-revoked) but does not re-check use_count (use was already counted at case-level access). This is intentional: once admitted to the session, the recipient can download all files within expiry |
| Integrity tampering | Every download (including via share) runs `_verify_and_decrypt`; records `INTEGRITY_VIOLATION` on failure |
| TOTP not verified for share creation | `require_recent_mfa` on share creation endpoints; 401 MFA_REQUIRED if step-up window expired |

---

## Edge Cases (cross-reference docs/EDGE_CASES.md)

| Scenario | Behaviour |
|----------|-----------|
| Document deleted after share created | `/info` still shows valid; `/download` returns 404 "Document not available" |
| Case archived after share created | `/info` returns 410; `/download` returns 410 |
| Case-scope share, one doc deleted after link created | That doc excluded from the list returned by `/download` (is_deleted filter) |
| Email casing mismatch | Compared case-insensitively via `.lower()` |
| Clock skew: expires_at one second in past | 410, no grace period |
| Two simultaneous exhaustion attempts | Atomic UPDATE with WHERE use_count < max_uses RETURNING — one succeeds, one gets 410 |
| CASE_OFFICER tries to revoke share they didn't create | 403 |
| Token with appended/stripped chars | SHA256 won't match → 404 (same response as not-found) |
| Integrity violation on share download | 422 INTEGRITY_VIOLATION; logs INTEGRITY_VIOLATION event |

---

## Review

### 1. Security holes?

- None found. Token entropy is 256 bits (infeasible to brute-force). Only hash stored in DB. Email gate is a deterrent, not a cryptographic control — documented clearly. Atomic increment prevents race condition. Integrity check runs on every download.

### 2. Contradictions with CLAUDE.md / docs/SECURITY.md?

- `allowed_email` is stated as REQUIRED in SECURITY.md but current `ShareCreateSchema` allows null. The new case-share schema enforces it. For the document share schema, `allowed_email` remains optional to not break the existing stub; the UI always populates it.

### 3. Simpler design?

- Could use a single `/share/{token}/access` endpoint for all scopes; chose `/download` + `/file/{doc_id}` to match the single-doc design and keep file streaming clean.

### 4. Edge cases from EDGE_CASES.md?

- ARCHIVED case: handled (410 on info/download)
- Integrity violations: handled (422 + audit event)
- Concurrent exhaustion: handled (atomic DB update)

### 5. Could this break existing features?

- `document_share_links.document_id` made nullable: existing NULL constraint dropped; backward compatible (existing DOCUMENT-scope rows still have document_id set). Migration is additive.
- New blueprints registered at new URL prefixes — no route conflicts.
- `AuditEventType.CASE_SHARED` added — no existing code references it; no conflict.
