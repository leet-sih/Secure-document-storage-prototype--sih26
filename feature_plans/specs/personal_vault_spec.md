# Spec: Personal Vault (user-scoped encrypted document storage)

## What and why

Any authenticated user can upload documents that are NOT tied to a case — their own
personal encrypted vault. Same AES-256-GCM chunked pipeline as case documents. Only the
uploader can see or download their own personal documents.

Use-cases: officer stores their own reference materials, working notes, or personal
evidence copies outside the case workflow.

---

## Exact files

**Create**
- `feature_plans/specs/personal_vault_spec.md` — this file
- `migrations/versions/004_personal_vault.py` — ALTER documents.case_id to nullable
- `frontend/src/pages/PersonalVaultPage.tsx` — new page

**Modify**
- `models/document.py` — `case_id` nullable=True
- `schemas/document_schemas.py` — `case_id` allow_none in response schema
- `services/document_service.py` — `upload_personal_document`, `list_personal_documents`,
  fix `download_document` + `soft_delete` for personal docs (case_id=None)
- `blueprints/documents.py` — `POST /me/documents`, `GET /me/documents`
- `components/DocumentUploader.tsx` — add `uploadUrl` prop so personal vault can reuse it
- `pages/CaseDetailPage.tsx` — replace "coming soon" placeholder with real upload + list
- `App.tsx` — add `/my-documents` route
- `components/AppShell.tsx` — add "My Vault" nav item
- `types/index.ts` — `caseId` optional in DocumentMeta

---

## Data model

No new tables. `documents.case_id` becomes nullable (NULL = personal document).

Personal document: `case_id IS NULL`, `uploaded_by = owner`.

---

## API

```
POST /api/v1/me/documents          — upload personal document (any auth role)
GET  /api/v1/me/documents          — list own personal documents
GET  /api/v1/documents/{id}/download — unchanged; personal docs: owner-only check
DELETE /api/v1/documents/{id}      — unchanged; personal docs: owner-only check
```

**Access rule:**
- `case_id IS NOT NULL` → existing case membership check via `case_service.user_has_access`
- `case_id IS NULL` → `uploaded_by == requesting_user_id`

---

## Security

| Threat | Mitigation |
|---|---|
| User accesses another user's personal doc | `uploaded_by == user_id` check; 404 on miss |
| Personal doc leaks into case listing | `list_documents` filters `case_id = ?` only |
| Case listing leaks personal docs | `list_personal_documents` filters `case_id IS NULL AND uploaded_by = ?` |
| CLOSED case gate not relevant | No case check for personal docs |

---

## Review

1. **Security holes?** Access control is symmetric: personal=owner-only, case=membership. 404 on miss (not 403). No cross-contamination between case and personal listings.
2. **Contradictions?** Making `case_id` nullable is a deliberate deviation from the original schema (nullable=False). Documented here. Migration is a single ALTER COLUMN — reversible unless personal docs exist.
3. **Simpler design?** Separate personal_documents table avoids schema change but duplicates the encryption pipeline. Nullable case_id is simpler.
4. **Edge cases?** `download_document` and `soft_delete` already use `case_service.user_has_access`; both updated to branch on `case_id IS None`.
5. **Break existing features?** Case document queries are all filtered by `case_id = ?` so personal docs never appear there. Migration is additive (null allowed where not-null was before).
