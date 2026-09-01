# Feature Spec: Case Management (full system)

**Author:** planning pass (Opus) · **Implementer:** Sonnet
**Branch:** `rjav_casemanagement`
**Source of truth:** `feature_plans/case_management_plan.md` (this spec extends it with **transfer** + frontend wiring)
**Status:** ready for implementation after the `## Review` section below.

---

## 1. What this feature does & why

A **Case** is the top-level access-control boundary. Every document, audit event, and
membership belongs to exactly one case. Access is **case-scoped**: a user sees a case only if
they are an active row in `case_members` (SUPER_ADMIN sees all). Non-members get **404, never
403** — we never confirm a case exists to someone who can't see it.

This feature delivers the complete case lifecycle so authorised users can:

1. **Create** a case (auto-owned by its department, creator becomes lead + CASE_OFFICER member).
2. **List / search / filter** the cases they can access (paginated).
3. **View** a case detail: metadata, members, activity timeline, and a slot for the document list.
4. **Update** metadata (title, description, priority, category) and drive the **status
   lifecycle** (`OPEN → UNDER_INVESTIGATION → CLOSED → ARCHIVED`) with server-enforced transitions.
5. **Add / remove members** (per-case role, soft removal) — the "add/remove people" requirement.
6. **Transfer** a case to another **department** *and* reassign the **lead officer** in one
   action, gated by **step-up TOTP MFA** — the "transfer case" requirement.
7. See a chronological **timeline** of everything that happened on the case.

It also exposes the **access-control helpers** (`user_has_access`, `get_accessible_case_ids`,
`get_case_for_user`, `get_user_role_in_case`, `assert_case_writable`) that the **document**,
**search**, and **audit** features call. Those callers are owned by other team members — we
**implement the helpers they import; we do not edit their files.**

> **Assigned cases appear automatically — no extra work needed.** When a user is added as a member
> (or installed as lead by transfer), the case shows up on their dashboard the next time they load
> `GET /cases`, because that endpoint returns exactly the cases where the user is an *active*
> `case_members` row (§4.2). This is a property of the membership-filtered list, not a separate
> feature. **Do NOT build any realtime push** (WebSockets/SSE/notification badge) — visibility on
> next page load/refresh is the intended prototype behaviour; live push is deferred.

### Explicitly OUT of scope (do not touch)
- **Document upload / download / delete internals** — `blueprints/documents.py`,
  `services/document_service.py`, `storage/`, chunk crypto. The document team owns these. The
  Documents tab in the UI renders an **integration slot** only (a placeholder that the document
  team mounts `DocumentList` / `DocumentUploader` into later). "Add files … will be wired later."
- **Core RBAC** — `core/rbac.py`, `core/security.py` are reused **as-is**. No edits.
- **Cross-department *sharing*** — deferred to the secure-link / document-sharing system
  (`feature_plans/document_sharing_plan.md`). This spec does **not** add a `case_shares` table or
  any department-level grant. (Transfer ≠ share: transfer *moves* ownership; sharing is handled
  elsewhere.)
- **Audit hash-chain** — `services/audit_service.py` write path. We only **read** `audit_events`
  for the timeline (a read query on the model; no new write helper there).

---

## 2. Exact files created / modified

### Backend — modify
| File | Change |
|---|---|
| `backend/app/core/audit_events.py` | Add `CASE_TRANSFERRED = "CASE_TRANSFERRED"` under the "Case management" block. |
| `backend/app/models/case.py` | Add `lead_officer_id` column (nullable FK → `users.id`). |
| `backend/app/schemas/case_schemas.py` | Add `CaseTransferSchema`; expand response schemas (list item, detail, member row, timeline event). |
| `backend/app/services/case_service.py` | Implement every stub + `assert_case_writable`, `transfer_case`, `list_members`, `get_case_timeline`, `get_transfer_options`. |
| `backend/app/blueprints/cases.py` | Implement all routes incl. `POST /{id}/transfer`, `GET /{id}/transfer-options`, and `GET /{id}/timeline`. |
| `backend/app/__init__.py` | Register `cases_bp` at `/api/v1/cases`. |

### Backend — create
| File | Change |
|---|---|
| `backend/migrations/versions/002_case_management.py` | Create `cases` + `case_members` tables, indexes, CHECK/UNIQUE constraints, `cases.lead_officer_id`, and an index on `audit_events.case_id`. `down_revision = "001_auth_totp"`. |
| `backend/tests/cases/test_case_create.py` | See §8. |
| `backend/tests/cases/test_case_access.py` | " |
| `backend/tests/cases/test_case_members.py` | " |
| `backend/tests/cases/test_case_status.py` | " |
| `backend/tests/cases/test_case_transfer.py` | " |

### Frontend — create
| File | Purpose |
|---|---|
| `frontend/src/components/AppShell.tsx` | Top-bar shell + nav (design: `AppShell.jsx`). |
| `frontend/src/components/CaseCard.tsx` | Dashboard case tile (design: `DashboardPage.jsx` → `CaseCard`). |
| `frontend/src/components/CreateCaseModal.tsx` | Create-case form (design: `CreateCaseModal.jsx`). |
| `frontend/src/components/AddMemberModal.tsx` | Add-member form (design: derived from `CreateUserModal`/`MembersTab`). |
| `frontend/src/components/TransferCaseModal.tsx` | **New** transfer modal (built from tokens; see §7.4). |
| `frontend/src/components/ConfirmModal.tsx` | Remove-member / destructive confirm (design: `ConfirmModal.jsx`). |
| `frontend/src/components/StepUpMfaModal.tsx` | Step-up TOTP prompt (design: `StepUpMfaModal.jsx`). |
| `frontend/src/pages/CaseDetailPage.tsx` | Case detail shell + Overview/Members/Activity/Documents tabs. |
| `frontend/src/lib/caseApi.ts` | Typed `apiFetch` wrappers for every case endpoint (incl. step-up retry helper). |

### Frontend — modify
| File | Change |
|---|---|
| `frontend/src/pages/DashboardPage.tsx` | Replace the placeholder landing with the real case list (grid, filters, create). |
| `frontend/src/App.tsx` | Add routes `/cases`, `/cases/:id`; make `/` redirect to `/cases`; wrap authed pages in `AppShell`. |
| `frontend/src/types/index.ts` | Extend `CaseSummary`; add `CaseDetail`, `CaseMember`, `TimelineEvent`, `CaseListResponse`. |

**Do not modify** any other file. In particular: `apiClient.ts`, `AuthContext.tsx`, `useAuth.ts`,
`rbac.py`, `security.py`, `documents.py`, `document_service.py`, `audit_service.py`.

---

## 3. Data model changes

### 3.1 `cases.lead_officer_id` (new column)
`Case.created_by` is **immutable** (who first created it — needed so historical audit resolves).
"Lead officer" is the **currently responsible** CASE_OFFICER and **changes on transfer**, so it
needs its own column.

```python
# models/case.py — add after department_id
lead_officer_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"))
```

- Set to `created_by` at creation.
- Reassigned by `transfer_case`.
- **Invariant:** the `lead_officer_id` user must always be an **active `CASE_OFFICER` member** of
  the case.

### 3.2 Migration `002_case_management.py`
Creates the two tables the models describe (they exist as SQLAlchemy classes but have **no
migration yet** — `001` only created departments/users/audit_events). Mirror the DDL in
`case_management_plan.md §Database Schema`, plus:

- `cases`: all columns from `models/case.py` **including `lead_officer_id UUID NULL REFERENCES users(id)`**.
  - `CONSTRAINT chk_case_status CHECK (status IN ('OPEN','UNDER_INVESTIGATION','CLOSED','ARCHIVED'))`
  - `CONSTRAINT chk_case_priority CHECK (priority IN ('LOW','NORMAL','HIGH','CRITICAL'))`
  - `case_number` UNIQUE.
- `case_members`: columns from `models/case_member.py`.
  - `UNIQUE (case_id, user_id)` = `uq_case_member`
  - `CHECK (role IN ('CASE_OFFICER','INVESTIGATOR','PROSECUTOR','VIEWER'))`
  - FKs `case_id`/`user_id` with `ON DELETE CASCADE`.
- Indexes: `ix_cases_department_id`, `ix_cases_status`, `ix_case_members_user_id`,
  `ix_case_members_case_id`, and **`ix_audit_events_case_id`** (speeds the timeline query;
  index-only, does not alter the audit table's data or the append-only grant).
- `down_revision = "001_auth_totp"`. `downgrade()` drops the two tables + the audit index.

> Note: `documents` table (other team) FKs `cases.id`. Their migration will chain after this one.
> Do not create the `documents` table here.

---

## 4. API contract

All routes are under `/api/v1/cases`. All require a valid access JWT (not an MFA temp token).
JSON bodies are validated through marshmallow (`unknown=RAISE`). Error envelope is the standard
`{"error": {code, message, request_id}}`.

### 4.1 `POST /api/v1/cases` — create — `[SUPER_ADMIN, CASE_OFFICER]`
Body → `CaseCreateSchema` (`case_number`, `title`, `description?`, `priority?`, `category?`).
- Server sets `department_id = creator.department_id`, `status=OPEN`,
  `created_by = lead_officer_id = creator.id`.
- Adds creator as active `CASE_OFFICER` in `case_members`.
- Audit `CASE_CREATED` (`target_type="case"`, `target_id=case.id`, `case_id=case.id`).
- **201** → `CaseDetailSchema`. Duplicate `case_number` → **409 CONFLICT**
  "Case number already exists".

### 4.2 `GET /api/v1/cases` — list — `[any authenticated]`
Query: `status`, `priority`, `category`, `search` (ILIKE on `title` OR `case_number`),
`mine` (`true`/`false`), `page` (default 1), `limit` (default 20, max 100).
- Non-super-admin: only cases where the user is an **active** member.
- SUPER_ADMIN: all cases; `mine=true` narrows to their memberships.
- Each item: `CaseListItemSchema` incl. `document_count` (Documents with `is_deleted=false AND
  status='ACTIVE'`) and `member_count` (active members).
- **200** → `{ "items": [...], "total": N, "page": P, "pages": Q }`.

### 4.3 `GET /api/v1/cases/{id}` — detail — `[members, SUPER_ADMIN; AUDITOR if ARCHIVED]`
- Access via `get_case_for_user` (→ 404 for non-members).
- Body: `CaseDetailSchema` incl. `created_by` (id/email/full_name), `lead_officer`
  (id/email/full_name), `department` (id/name), `members[]`, `document_summary`
  (`{total, by_type:{...}}`), timestamps.
- Audit `CASE_ACCESSED` (`case_id=id`). *(Record once per GET; acceptable for the prototype.)*
- **200**.

### 4.4 `PATCH /api/v1/cases/{id}` — update — `[lead CASE_OFFICER / any active CASE_OFFICER member, SUPER_ADMIN]`
Body → `CasePatchSchema` (any subset of `title`, `description`, `priority`, `category`, `status`).
- **Authorization:** SUPER_ADMIN, or an **active `CASE_OFFICER` member** of this case. Other
  members / roles → **404** (route is reachable only after `get_case_for_user`; a non-CASE_OFFICER
  member who can *see* the case but not edit gets **403 FORBIDDEN** — they already know it exists).
- **Status transitions** enforced server-side (see §5). Illegal transition → **409 CONFLICT**.
- On `status→CLOSED`: set `closed_at`; audit `CASE_CLOSED`. On `→ARCHIVED`: set `archived_at`.
  Otherwise audit `CASE_UPDATED` with a metadata list of changed fields (names only, **no values
  that could be sensitive** — field names only).
- **200** → `CaseDetailSchema`.

### 4.5 `POST /api/v1/cases/{id}/members` — add member — `[CASE_OFFICER member, SUPER_ADMIN]`
Body → `CaseMemberAddSchema` (`user_id`, `role`).
- Target user must exist and be `is_active` → else **404**/**400**.
- Duplicate active membership → **409 CONFLICT** "User is already a member".
- If a **soft-removed** row exists (`is_active=false`): reactivate it (set `is_active=true`,
  `removed_at=null`, update `role`, `added_by`, `added_at`) rather than inserting (respects the
  `uq_case_member` unique constraint).
- Audit `CASE_MEMBER_ADDED` (`target_type="user"`, `target_id=user_id`, `case_id=id`,
  metadata `{role}`).
- **201** → `CaseMemberSchema`.

### 4.6 `DELETE /api/v1/cases/{id}/members/{user_id}` — soft-remove — `[CASE_OFFICER member, SUPER_ADMIN]`
- Soft removal: `is_active=false`, `removed_at=now()`.
- **Guards:** cannot remove **self** (409 "You cannot remove yourself"); cannot remove the
  **last active CASE_OFFICER** (409 "Cannot remove the last case officer — assign another
  first"); if the removed user is the current `lead_officer_id`, block with 409 "Reassign the
  lead officer before removing them" (forces transfer/patch first — keeps the invariant).
- Audit `CASE_MEMBER_REMOVED`.
- **204**.

### 4.7 `POST /api/v1/cases/{id}/transfer` — **transfer** — `[lead CASE_OFFICER member, SUPER_ADMIN]` + **step-up MFA**
**New.** Decorated with `@require_recent_mfa()` (uses `MFA_STEP_UP_MINUTES`, default 15). If the
JWT's `mfa_at` is stale → **401 `MFA_REQUIRED`** (frontend opens the step-up modal, re-verifies,
retries).

Body → `CaseTransferSchema`:
```json
{ "to_department_id": "uuid", "new_lead_officer_id": "uuid" }
```
Server behaviour (single DB transaction):
1. `get_case_for_user` (404 if not visible). Authz: SUPER_ADMIN or the current lead CASE_OFFICER.
2. Reject if `status == 'ARCHIVED'` → **409** "Archived cases cannot be transferred".
3. `to_department_id` must exist → **404** "Department not found".
4. `new_lead_officer_id` must be an **active user** whose **system role** is `CASE_OFFICER` (or
   `SUPER_ADMIN`) → else **400** "New lead must be an active case officer". Recommended (and
   validated): the new lead **belongs to `to_department_id`** → else **400** "New lead must be in
   the target department".
5. Set `case.department_id = to_department_id`, `case.lead_officer_id = new_lead_officer_id`,
   bump `updated_at`.
6. Ensure the new lead is an **active `CASE_OFFICER` member** (insert or reactivate/upgrade).
   The previous lead is **retained** as a member (not auto-removed).
7. Audit `CASE_TRANSFERRED` (`target_type="case"`, `target_id=id`, `case_id=id`, metadata
   `{from_department_id, to_department_id, from_lead_officer_id, to_lead_officer_id}` — all IDs,
   no PII).
8. **200** → `CaseDetailSchema`.

### 4.8 `GET /api/v1/cases/{id}/timeline` — activity feed — `[members, SUPER_ADMIN]`
Query: `limit` (default 50, max 200), `before_id` (BIGINT cursor for "load more").
- Access via `get_case_for_user`.
- Read-only query on `audit_events WHERE case_id = :id ORDER BY id DESC LIMIT :limit`
  (`id < before_id` when the cursor is given). `prev_hash`/`this_hash` are **never** serialized.
- Resolve `actor_user_id → {email, full_name, role}` (batch-load to avoid N+1).
- **200** → `{ "events": [TimelineEventSchema...], "next_before_id": <bigint|null> }`.

### 4.9 `GET /api/v1/cases/{id}/transfer-options` — **new** — `[lead CASE_OFFICER member, SUPER_ADMIN]`
Case-manager-scoped picker data so a **lead CASE_OFFICER** (not just SUPER_ADMIN) can populate the
Transfer modal without needing the SUPER_ADMIN-only `GET /users` / `GET /users/departments` routes.
- Authz: SUPER_ADMIN or the current lead CASE_OFFICER of this case (same gate as transfer). Anyone
  else who can see the case → **403**; non-members → **404** (via `get_case_for_user`).
- Returns:
  ```json
  {
    "departments": [ { "id": "...", "name": "..." } ],
    "officers":    [ { "id": "...", "full_name": "...", "email": "...", "department_id": "..." } ]
  }
  ```
  - `departments`: all departments (id + name only).
  - `officers`: active users whose **system role** ∈ {`CASE_OFFICER`, `SUPER_ADMIN`} — the users
    eligible to be a new lead. The UI filters `officers` by the chosen department client-side.
- **Deliberately minimal disclosure:** returns only officer identity needed to pick a recipient
  (name/email/dept) — never password/MFA/lockout fields. No pagination needed (officer count is
  small in the prototype); cap the query at 500 rows defensively.
- **200**.

---

## 5. Status lifecycle (server-enforced)

Allowed transitions (from `case_management_plan.md §Case Lifecycle`):

```
OPEN                → UNDER_INVESTIGATION           [CASE_OFFICER member, SUPER_ADMIN]
UNDER_INVESTIGATION → CLOSED                        [CASE_OFFICER member, SUPER_ADMIN]
CLOSED              → OPEN                           [SUPER_ADMIN only]      (reopen)
CLOSED              → ARCHIVED                       [SUPER_ADMIN only]
ARCHIVED            → (terminal — no transitions out)
```

- Same-status "transition" (no `status` in body, or unchanged) is allowed for metadata-only PATCH.
- Any pair not in the table → **409 CONFLICT** "Illegal status transition: X → Y".
- `CLOSED→OPEN` and `CLOSED→ARCHIVED` require **SUPER_ADMIN** even though a CASE_OFFICER may PATCH
  other fields — enforce the actor check per-transition.

**Write-gate helper** (`assert_case_writable(case)`): raises **409 CONFLICT** "Case is
{closed|archived} — no changes allowed" when `status in ('CLOSED','ARCHIVED')`. The document team
calls this before upload/delete. We provide it; we do not wire it into their routes.

**ARCHIVED access rule** (`get_case_for_user`): if `status == 'ARCHIVED'`, only SUPER_ADMIN and
AUDITOR may access; everyone else (even a former member) gets **404**.

---

## 6. Schemas (`case_schemas.py`)

Keep the existing `CaseCreateSchema`, `CasePatchSchema`, `CaseMemberAddSchema` (they already
match the plan). **Add / expand**:

```python
class CaseTransferSchema(_Base):
    to_department_id   = fields.UUID(required=True)
    new_lead_officer_id = fields.UUID(required=True)

# --- responses (dump-only) ---
class _UserBriefSchema(Schema):
    id = fields.UUID(); email = fields.Str(); full_name = fields.Str(); role = fields.Str()

class _DeptBriefSchema(Schema):
    id = fields.UUID(); name = fields.Str()

class CaseMemberSchema(Schema):          # one members[] row
    user_id = fields.UUID(); email = fields.Str(); full_name = fields.Str()
    role = fields.Str(); department = fields.Str()      # dept name for the table
    added_at = fields.DateTime()

class CaseListItemSchema(Schema):        # GET /cases items[]
    id, case_number, title, status, priority, category = ...
    document_count = fields.Int(); member_count = fields.Int()
    created_at, updated_at = fields.DateTime()

class CaseDetailSchema(Schema):          # GET /cases/{id}, POST, PATCH, transfer
    id, case_number, title, description, status, priority, category = ...
    created_by = fields.Nested(_UserBriefSchema)
    lead_officer = fields.Nested(_UserBriefSchema)
    department = fields.Nested(_DeptBriefSchema)
    members = fields.List(fields.Nested(CaseMemberSchema))
    document_summary = fields.Dict()     # {"total": N, "by_type": {DOC_TYPE: n}}
    created_at, updated_at, closed_at, archived_at = fields.DateTime()

class TimelineEventSchema(Schema):       # GET /cases/{id}/timeline events[]
    id = fields.Int()                    # audit BIGSERIAL, used as before_id cursor
    event_type = fields.Str()
    actor = fields.Nested(_UserBriefSchema, allow_none=True)   # null for system events
    target_type = fields.Str(allow_none=True)
    metadata = fields.Dict()             # from event_metadata; never prev/this_hash
    created_at = fields.DateTime()

class _OfficerOptionSchema(Schema):      # transfer-options officers[]
    id = fields.UUID(); full_name = fields.Str()
    email = fields.Str(); department_id = fields.UUID()

class TransferOptionsSchema(Schema):     # GET /cases/{id}/transfer-options
    departments = fields.List(fields.Nested(_DeptBriefSchema))
    officers = fields.List(fields.Nested(_OfficerOptionSchema))
```
Field names in responses are **snake_case** (matches the rest of the API; the frontend maps to
camelCase in `caseApi.ts`, as `useAuth.ts` already does for `full_name` etc.).

---

## 7. Frontend

Design tokens come from `design/screens/tokens.js` (import `C`, `ROLE_LABEL`, `ROLE_COLOR`,
`STATUS_COLOR`, `PRIORITY_COLOR`, `SEV`, icon maps). **Do not hardcode token hexes**; reference
the token constants. Match the referenced JSX layouts exactly; replace all mock props with real
`apiFetch` data. Delete prototype-only controls (e.g. the "preview as role" menu in `AppShell`).

### 7.1 Routing (`App.tsx`)
- `/` → `<Navigate to="/cases" replace />`.
- `/cases` → `ProtectedRoute` → `AppShell` → `DashboardPage`.
- `/cases/:id` → `ProtectedRoute` → `AppShell` → `CaseDetailPage`.
- Keep `/admin/users` (SUPER_ADMIN). Wrap authed pages in `AppShell` (top-bar nav: Cases,
  Search[disabled/placeholder], Audit[placeholder], Admin[SUPER_ADMIN], Profile via user menu).

### 7.2 Dashboard (`DashboardPage.tsx` + `CaseCard.tsx`) — design `DashboardPage.jsx`
- On mount: `GET /cases` with current filters → render grid of `CaseCard`.
- `canCreateCase` = role ∈ {SUPER_ADMIN, CASE_OFFICER} → show **New Case** → `CreateCaseModal`.
- Search input (debounced) → `search` param; status/priority selects; "My cases" toggle → `mine`.
- Status/priority badges use `STATUS_COLOR`/`PRIORITY_COLOR`. Empty result → empty state.
- `CaseCard.open` → `navigate('/cases/'+id)`.

### 7.3 Case detail (`CaseDetailPage.tsx`) — designs `CaseDetailPage.jsx` + tabs
- On mount: `GET /cases/:id` → header (title, status/priority badges, counts, created date).
- Tabs: **Documents** | **Activity** | **Members** | **Overview** (order per `CaseDetailPage.jsx`).
  - **Documents tab:** render an integration **slot** — a bordered placeholder container with a
    comment `{/* document team mounts <DocumentList/> + <DocumentUploader/> here */}`. No fetch,
    no upload logic. (This is the "add files wired later" slot.)
  - **Activity tab** (`ActivityTab.jsx`): `GET /cases/:id/timeline`; map events to
    `{icon, color (SEV[event_type]||C.ts), actor, roleLabel (ROLE_LABEL), event, target, when}`;
    "Load more" uses `next_before_id`.
  - **Members tab** (`MembersTab.jsx`): render `members[]`; **Add Member** (if actor may manage —
    SUPER_ADMIN or CASE_OFFICER member) → `AddMemberModal`; per-row **Remove** →
    `ConfirmModal` → `DELETE …/members/:uid`. `canRemove` hidden for self and for the lead officer.
  - **Overview tab** (`OverviewTab.jsx`): editable title/description/priority/status +
    read-only case number, created by, created at. **Save** → `PATCH /cases/:id`. Show "Saved at
    HH:MM" in `C.succ` on success. Status `<select>` options restricted to legal next states for
    the current status + role (compute client-side; server is the real gate). Add a **Transfer**
    button here (top-right of Overview) — visible to **SUPER_ADMIN or the lead CASE_OFFICER**
    (i.e. `user.id === detail.leadOfficer.id` or role `SUPER_ADMIN`) — that opens `TransferCaseModal`.

### 7.4 Transfer modal (`TransferCaseModal.tsx`) — **no prototype screen; build from tokens**
Match `CreateCaseModal.jsx` structure/spacing/tokens (512px card, `C.elev` bg, `C.bsub` border).
Both selects are populated from the **case-scoped** `GET /cases/:id/transfer-options` (§4.9) — so a
**lead CASE_OFFICER can transfer from the UI**, not only SUPER_ADMIN. Do **not** call the
SUPER_ADMIN-only `GET /users` / `GET /users/departments` here.

- On modal open: `GET /cases/:id/transfer-options` → `{ departments, officers }`.
- **Target department** `<select>` — from `departments`.
- **New lead officer** `<select>` — from `officers` filtered client-side by the chosen
  `department_id`. Disable Confirm until both are chosen and the officer belongs to the department.
- **Confirm** → `POST /cases/:id/transfer` via the `withStepUp` helper. On **401 MFA_REQUIRED**,
  open `StepUpMfaModal`; after successful step-up retry the transfer (§7.5). On success, close the
  modal and refetch case detail. Surface backend 400s (e.g. "New lead must be in the target
  department") inline.

### 7.5 Step-up MFA wiring (`StepUpMfaModal.tsx` + `caseApi.ts`) — design `StepUpMfaModal.jsx`
`caseApi.ts` exposes a `withStepUp(fn)` helper:
1. Call the sensitive endpoint.
2. If it throws `ApiError` with `code === "MFA_REQUIRED"`, resolve by opening the step-up modal.
3. Modal collects a 6-digit code → `POST /auth/mfa/step-up {totp_code}` → `{access_token}`.
4. Persist the new token via `AuthContext.setSession(token, currentUser)` (token carries a fresh
   `mfa_at`). **Do not modify `AuthContext`/`useAuth`** — call the existing `setSession` from the
   component that owns the modal (`useAuth()` from the store).
5. Retry the original call. On repeated `MFA_STEP_UP` failure show `stepUpError`.

### 7.6 Types (`types/index.ts`)
Extend `CaseSummary` (add `category`, `updatedAt`) and add:
```ts
export interface CaseMember { userId, email, fullName, role, department, addedAt }
export interface CaseDetail {
  id, caseNumber, title, description, status, priority, category,
  createdBy: UserBrief, leadOfficer: UserBrief, department: {id,name},
  members: CaseMember[], documentSummary: {total:number, byType:Record<string,number>},
  createdAt, updatedAt, closedAt, archivedAt
}
export interface TimelineEvent { id:number, eventType, actor: UserBrief|null, targetType, metadata, createdAt }
export interface CaseListResponse { items: CaseSummary[], total, page, pages }
```
(`UserBrief = { id, email, fullName, role }`.) Keep in sync with the marshmallow response
shapes; `caseApi.ts` maps snake_case → camelCase.

---

## 8. Testing (pytest, backend)

`tests/cases/`:
- **test_case_create:** officer/admin can create; investigator → 403; duplicate `case_number` →
  409; creator auto-added as active CASE_OFFICER member; `lead_officer_id == created_by`;
  `CASE_CREATED` recorded.
- **test_case_access:** member can GET detail; non-member → **404 not 403**; SUPER_ADMIN sees all;
  ARCHIVED case → non-admin/non-auditor 404; `CASE_ACCESSED` recorded; `get_accessible_case_ids`
  returns only active memberships (all for super-admin).
- **test_case_members:** add member; duplicate active → 409; soft-removed row reactivates instead
  of duplicate-insert; remove soft-deletes; cannot remove self; cannot remove last CASE_OFFICER;
  cannot remove current lead; removed member loses `user_has_access`.
- **test_case_status:** each legal transition; illegal transition → 409; CLOSED→OPEN/ARCHIVED
  requires SUPER_ADMIN (CASE_OFFICER → 403/409 as specified); `assert_case_writable` raises on
  CLOSED & ARCHIVED, passes on OPEN/UNDER_INVESTIGATION.
- **test_case_transfer:** happy path moves department + lead and adds new lead as CASE_OFFICER
  member; **lead CASE_OFFICER (not admin) can transfer**; stale `mfa_at` → 401 MFA_REQUIRED; new
  lead not in target dept → 400; new lead inactive → 400; ARCHIVED case → 409; non-lead
  non-admin member → 403; non-member → 404; `CASE_TRANSFERRED` recorded with ID-only metadata.
- **test_transfer_options:** lead CASE_OFFICER and SUPER_ADMIN get `{departments, officers}`;
  officers list contains only active CASE_OFFICER/SUPER_ADMIN users and no password/MFA fields;
  a non-lead member → 403; non-member → 404.

Write crypto/auth-adjacent assertions (the step-up gate) explicitly. Use the existing test
fixtures/patterns from `tests/` (seeded departments/users, JWT minting).

---

## 9. Security threat model

| Threat | Mitigation |
|---|---|
| Horizontal escalation (see another dept's cases) | All reads go through `get_case_for_user`/`get_accessible_case_ids`; non-members get 404, never 403. |
| Enumerate case existence via status codes | Uniform 404 for non-members; 403 only when the user already provably sees the case (member but wrong role on PATCH/members). |
| Privilege escalation via transfer | Transfer gated to SUPER_ADMIN / lead CASE_OFFICER **and** `@require_recent_mfa` (fresh TOTP). New lead must be an active CASE_OFFICER in the target dept. |
| Officer-list disclosure via `transfer-options` | Endpoint is gated to the same actors as transfer (SUPER_ADMIN / lead CASE_OFFICER of *this* case); returns only officer id/name/email/dept — never credential/MFA/lockout fields. A lead officer already needs recipient identities to transfer; disclosure is minimal and necessary. |
| Orphaned case (no officer) | Guards: can't remove last CASE_OFFICER; can't remove the current lead; transfer always installs a valid lead. |
| Writing to closed/archived cases | `assert_case_writable` + transition matrix; ARCHIVED is terminal + admin/auditor-only read. |
| Audit tampering / leakage | Timeline is **read-only** on `audit_events`; never serializes `prev_hash`/`this_hash`; metadata is IDs/field-names only — no PII/values. |
| Injection | All input via marshmallow (`unknown=RAISE`); all queries parameterized via SQLAlchemy; no string interpolation. |
| MFA replay across the step-up window | Reuses the existing `mfa_at` JWT claim + `MFA_STEP_UP_MINUTES`; no new token logic. |
| Mass data exposure via list | Pagination capped (`limit ≤ 100`); membership filter applied in the query, not post-filtered in Python. |

---

## 10. Open questions / assumptions

1. **Transfer UI audience — RESOLVED.** Both **SUPER_ADMIN and the lead CASE_OFFICER** can
   transfer from the UI. This is powered by the case-scoped `GET /cases/{id}/transfer-options`
   (§4.9), which returns departments + eligible officers without needing any SUPER_ADMIN-only
   route. Non-lead members do not see the Transfer button (and get 403 at the API).
2. **`CASE_ACCESSED` volume.** Recording an audit row on every detail GET is chatty. *Assumption:*
   record it (matches the plan). Say if you'd rather throttle/skip.
3. **Lead retained on transfer.** The previous lead stays a CASE_OFFICER member after transfer
   (not auto-removed). *Assumption per "reassign", not "eject".*
4. **New-lead department rule.** We require the new lead to belong to the target department.
   Relax to "any active CASE_OFFICER" if cross-posting officers is desired.
5. **Departments for create.** A case inherits the **creator's** department; there is no
   department picker on create (matches `CreateCaseModal.jsx`, which has none).

---

## Review

**1. Security holes?**
- Transfer is the highest-risk action; it is gated by both RBAC (SUPER_ADMIN / lead CASE_OFFICER)
  and `@require_recent_mfa`, and validates the new lead is an active CASE_OFFICER in the target
  dept — no way to hand a case to an arbitrary/inactive user. Timeline reads never expose chain
  hashes or PII. The one residual risk is the PATCH authz split (403 vs 404): we only return 403
  to users who are already members (so existence is not leaked to outsiders) — consistent with
  the plan's "404 for non-members" rule. No plaintext, keys, or secrets touched.

**2. Contradicts CLAUDE.md / SECURITY.md / the plan?**
- No. It **extends** `case_management_plan.md` (transfer + `lead_officer_id` are additive). Uses
  marshmallow everywhere, parameterized queries, `pg_advisory_xact_lock` is untouched (we don't
  write audit). Terminology: "hash-chained, tamper-evident", "least-privilege". Cross-department
  **sharing** is explicitly deferred to the sharing system per your decision — not implemented here.
- One deviation to flag: adds a **column + migration** (`lead_officer_id`) and an **audit enum
  value** (`CASE_TRANSFERRED`). Both are required by the transfer feature; the audit enum is the
  designated single source of truth and the plan says "add new events HERE first" — compliant.

**3. Simpler design meeting the same requirements?**
- We considered representing "lead officer" purely via a CASE_OFFICER membership (no new column).
  Rejected: transfer must *reassign a single responsible officer* and the invariant needs an
  unambiguous target; a column is the honest, minimal representation. Cross-dept share was
  dropped entirely (deferred), which removed a whole table and endpoint set — already simplified.

**4. Which `docs/EDGE_CASES.md` cases apply & handled?**
- Duplicate `case_number` → 409 (§4.1). Closed/archived write attempts → `assert_case_writable`
  409 (§5). Non-member GET → 404 (§4.3). Last CASE_OFFICER removal blocked (§4.6). ARCHIVED
  read-only + admin/auditor-only (§5). Empty search → returns all accessible (query builder skips
  empty filter). Soft-removed member re-add handled via reactivation (§4.5). *(Re-read
  `docs/EDGE_CASES.md` before coding to confirm no newer cross-cutting cases were added.)*

**5. Could this break existing features?**
- Risk: `documents`/`search`/`audit` import `case_service` helpers that are currently
  `NotImplementedError`. Implementing them is strictly additive and unblocks those callers — no
  signature changes to the documented helpers (`user_has_access`, `get_case_for_user`,
  `get_user_role_in_case`, `get_accessible_case_ids`), plus the new `assert_case_writable`.
  Migration `002` chains off `001` and only **creates** tables/indexes, so existing auth tables
  are untouched. Registering `cases_bp` is additive. Frontend `DashboardPage`/`App.tsx` changes
  replace placeholder scaffolding only. **Mitigation:** run the full test suite + `flask db
  upgrade` on a fresh DB before merging; do not edit any document-team file.
