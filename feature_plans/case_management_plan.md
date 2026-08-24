# Feature Plan: Case Management

## What Is This Feature?

A Case is the top-level container for everything in the system. Every document, audit event, and member assignment belongs to a case. Cases represent real-world legal proceedings: an FIR investigation, a court case, a forensic analysis request.

The case management feature provides:
- Creation and lifecycle management of cases
- Assigning users to cases with specific roles
- Restricting document access to only members of a case
- Viewing a chronological timeline of all activity on a case

---

## Why Cases Are the Access Control Boundary

The system does not use a flat permission model ("this user can see all documents"). Instead, access is case-scoped:

```
User A (INVESTIGATOR) is a member of Case #123
  → Can access all documents in Case #123
  → Cannot see Case #456 exists
  → Cannot even get a 403 on Case #456 — gets a 404 (case doesn't exist to them)

User B (CASE_OFFICER) created Case #456
  → Full access to Case #456
  → No access to Case #123 (unless explicitly added)
```

This prevents horizontal privilege escalation: an attacker who compromises an investigator account cannot access cases outside that investigator's assignments.

---

## Case Lifecycle

```
OPEN → UNDER_INVESTIGATION → CLOSED → ARCHIVED

Transitions:
  OPEN             → UNDER_INVESTIGATION  (by CASE_OFFICER when investigation begins)
  UNDER_INVESTIGATION → CLOSED            (by CASE_OFFICER or SUPER_ADMIN)
  CLOSED           → OPEN                 (by SUPER_ADMIN only — case reopened)
  CLOSED           → ARCHIVED             (by SUPER_ADMIN — read-only, no new documents)
  ARCHIVED         → (terminal)           (cannot transition out)
```

Rules per status:
- `OPEN`, `UNDER_INVESTIGATION`: Documents can be uploaded and deleted
- `CLOSED`: Documents are read-only (no upload, no delete)
- `ARCHIVED`: Read-only, and only SUPER_ADMIN and AUDITOR can access

---

## Database Schema

```sql
CREATE TABLE departments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,           -- "Cybercrime Unit", "Forensic Lab", etc.
    dept_type   TEXT NOT NULL,                  -- "POLICE", "COURT", "FORENSIC", "LEGAL"
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cases (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_number     TEXT NOT NULL UNIQUE,       -- "FIR-2026-DL-001" (human-readable)
    title           TEXT NOT NULL,
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'OPEN',
    priority        TEXT NOT NULL DEFAULT 'NORMAL',    -- LOW | NORMAL | HIGH | CRITICAL
    category        TEXT,                       -- "CYBERCRIME", "HOMICIDE", "FRAUD", etc.
    created_by      UUID NOT NULL REFERENCES users(id),
    department_id   UUID NOT NULL REFERENCES departments(id),
    closed_at       TIMESTAMPTZ,
    archived_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT chk_case_status
        CHECK (status IN ('OPEN', 'UNDER_INVESTIGATION', 'CLOSED', 'ARCHIVED')),
    CONSTRAINT chk_priority
        CHECK (priority IN ('LOW', 'NORMAL', 'HIGH', 'CRITICAL'))
);

CREATE TABLE case_members (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id     UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,                  -- role within this case (not the user's system role)
    added_by    UUID NOT NULL REFERENCES users(id),
    added_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    removed_at  TIMESTAMPTZ,                    -- soft removal
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,

    CONSTRAINT uq_case_member UNIQUE (case_id, user_id),
    CONSTRAINT chk_case_member_role
        CHECK (role IN ('CASE_OFFICER', 'INVESTIGATOR', 'PROSECUTOR', 'VIEWER'))
);

-- View: active case members only
CREATE VIEW active_case_members AS
    SELECT * FROM case_members WHERE is_active = TRUE;
```

### Why a separate `case_members.role` from `users.role`?

A user might be an INVESTIGATOR on Case A but act as a VIEWER on Case B (forwarded case, read-only access). The case-level role allows fine-grained scoping without changing the user's system-wide role.

---

## API Endpoints

### POST /api/v1/cases `[SUPER_ADMIN, CASE_OFFICER]`

```json
// Request
{
  "case_number": "FIR-2026-DL-001",
  "title": "Cybercrime Investigation - Data Breach",
  "description": "...",
  "priority": "HIGH",
  "category": "CYBERCRIME"
}

// Response 201
{
  "id": "uuid",
  "case_number": "FIR-2026-DL-001",
  "title": "...",
  "status": "OPEN",
  "priority": "HIGH",
  "created_by": { "id": "...", "email": "..." },
  "created_at": "..."
}
```

Server behavior:
1. Validate schema
2. Check case_number uniqueness
3. Create case with `status=OPEN`
4. Add creator as a CASE_OFFICER member in `case_members`
5. Record AuditEvent: CASE_CREATED

### GET /api/v1/cases `[All authenticated roles]`

Returns only cases the current user is a member of (via `case_members`).
SUPER_ADMIN sees all cases.

Query params: `status`, `priority`, `category`, `search` (searches title + case_number), `page`, `limit`

```json
{
  "items": [
    {
      "id": "...",
      "case_number": "FIR-2026-DL-001",
      "title": "...",
      "status": "UNDER_INVESTIGATION",
      "priority": "HIGH",
      "document_count": 14,
      "member_count": 3,
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "total": 5,
  "page": 1,
  "pages": 1
}
```

### GET /api/v1/cases/{id} `[Case members, SUPER_ADMIN]`

Returns case detail including member list and document summary (counts by type, no content).

```json
{
  "id": "...",
  "case_number": "FIR-2026-DL-001",
  "title": "...",
  "description": "...",
  "status": "UNDER_INVESTIGATION",
  "priority": "HIGH",
  "category": "CYBERCRIME",
  "created_by": { "id": "...", "email": "...", "role": "CASE_OFFICER" },
  "department": { "id": "...", "name": "Cybercrime Unit" },
  "members": [
    { "user_id": "...", "email": "...", "role": "INVESTIGATOR", "added_at": "..." }
  ],
  "document_summary": {
    "total": 14,
    "by_type": { "FIR": 1, "INVESTIGATION_RECORD": 8, "FORENSIC_REPORT": 5 }
  },
  "created_at": "...",
  "updated_at": "..."
}
```

Records AuditEvent: CASE_ACCESSED

### PATCH /api/v1/cases/{id} `[CASE_OFFICER (own case), SUPER_ADMIN]`

Updatable fields: `title`, `description`, `priority`, `category`, `status`

Status transition rules enforced server-side. Invalid transitions return 409.

```json
// Request
{ "status": "UNDER_INVESTIGATION" }
```

### POST /api/v1/cases/{id}/members `[CASE_OFFICER (own case), SUPER_ADMIN]`

```json
// Request
{ "user_id": "uuid", "role": "INVESTIGATOR" }

// Response 201
{ "case_id": "...", "user_id": "...", "role": "INVESTIGATOR", "added_at": "..." }
```

Validation:
- User must exist and be active
- User must not already be a member (409 if duplicate)
- PROSECUTOR and VIEWER can only be added by SUPER_ADMIN or CASE_OFFICER

Records AuditEvent: CASE_MEMBER_ADDED

### DELETE /api/v1/cases/{id}/members/{user_id} `[CASE_OFFICER, SUPER_ADMIN]`

Soft removal: sets `is_active=False` and `removed_at=now()`. The member's historical audit events still reference their user ID.

A user cannot remove themselves.

Records AuditEvent: CASE_MEMBER_REMOVED

### GET /api/v1/cases/{id}/timeline

Returns chronological list of all audit events for this case, formatted for display (not raw audit format). Accessible to all case members.

```json
{
  "events": [
    {
      "timestamp": "2026-08-25T10:00:00Z",
      "type": "DOCUMENT_UPLOADED",
      "actor": "officer@police.gov.in",
      "description": "Uploaded FIR_001.pdf"
    },
    {
      "timestamp": "2026-08-25T11:30:00Z",
      "type": "CASE_MEMBER_ADDED",
      "actor": "officer@police.gov.in",
      "description": "Added investigator@forensics.gov.in as INVESTIGATOR"
    }
  ]
}
```

---

## Access Control Implementation

```python
# services/case_service.py

def get_case_for_user(case_id: str, user_id: str) -> Case:
    """
    Returns the case if user has access, raises 404 otherwise.
    We raise 404 (not 403) to avoid leaking that the case exists.
    """
    case = Case.query.get(case_id)
    if case is None:
        abort(404)

    if current_user_is_super_admin():
        return case

    membership = CaseMember.query.filter_by(
        case_id=case_id, user_id=user_id, is_active=True
    ).first()

    if membership is None:
        abort(404)  # Not 403 — don't reveal existence

    return case

def user_has_access(user_id: str, case_id: str) -> bool:
    """Used by document service to check access without aborting."""
    if user_is_super_admin(user_id):
        return True
    return CaseMember.query.filter_by(
        case_id=case_id, user_id=user_id, is_active=True
    ).first() is not None

def get_user_role_in_case(user_id: str, case_id: str) -> str | None:
    """Returns the user's case-level role, or None if not a member."""
    member = CaseMember.query.filter_by(
        case_id=case_id, user_id=user_id, is_active=True
    ).first()
    return member.role if member else None
```

---

## marshmallow Schemas

```python
class CaseCreateSchema(Schema):
    case_number = fields.Str(required=True, validate=[
        validate.Length(min=3, max=50),
        validate.Regexp(r'^[A-Za-z0-9\-\/]+$', error="Only letters, numbers, hyphens, slashes")
    ])
    title       = fields.Str(required=True, validate=validate.Length(min=3, max=255))
    description = fields.Str(load_default=None, validate=validate.Length(max=2000))
    priority    = fields.Str(load_default="NORMAL",
                             validate=validate.OneOf(["LOW", "NORMAL", "HIGH", "CRITICAL"]))
    category    = fields.Str(load_default=None, validate=validate.Length(max=100))

class CasePatchSchema(Schema):
    title       = fields.Str(validate=validate.Length(min=3, max=255))
    description = fields.Str(validate=validate.Length(max=2000))
    priority    = fields.Str(validate=validate.OneOf(["LOW", "NORMAL", "HIGH", "CRITICAL"]))
    category    = fields.Str(validate=validate.Length(max=100))
    status      = fields.Str(validate=validate.OneOf([
                    "OPEN", "UNDER_INVESTIGATION", "CLOSED", "ARCHIVED"]))

class CaseMemberAddSchema(Schema):
    user_id = fields.UUID(required=True)
    role    = fields.Str(required=True, validate=validate.OneOf([
                "CASE_OFFICER", "INVESTIGATOR", "PROSECUTOR", "VIEWER"]))
```

---

## Frontend Components

| Component | Route | Description |
|-----------|-------|-------------|
| `CaseDashboard` | `/cases` | Card grid of accessible cases; status badge; priority colour; document count |
| `CaseCreateModal` | `/cases` (modal) | Form to create a new case |
| `CaseDetailPage` | `/cases/{id}` | Title, status, members list, document list, timeline tab |
| `CaseStatusBadge` | Everywhere | Color-coded pill: OPEN=blue, UNDER_INVESTIGATION=yellow, CLOSED=grey, ARCHIVED=dark |
| `MemberManagement` | `/cases/{id}/members` | Add/remove members, assign roles |
| `CaseTimeline` | `/cases/{id}/timeline` | Chronological feed of case activity |
| `CaseSearchBar` | `/cases` | Search by case_number or title |

---

## Edge Cases

| Scenario | Behaviour |
|----------|-----------|
| Duplicate case_number | 409 Conflict with message "Case number already exists" |
| Status: CLOSED, user tries to upload | 409 "Case is closed — no new documents allowed" |
| Non-member tries to GET /cases/{id} | 404 (not 403) |
| CASE_OFFICER tries to add another CASE_OFFICER | Allowed (co-officers on a case) |
| Last CASE_OFFICER removed from case | Prevent: "Cannot remove the last CASE_OFFICER — assign another first" |
| Case with documents is ARCHIVED | Documents become read-only; downloads still work; uploads blocked |
| Search query is empty string | Return all accessible cases (no filter) |

---

## Testing Plan

```
tests/cases/
├── test_case_create.py
│   ├── test_case_officer_can_create_case
│   ├── test_investigator_cannot_create_case
│   ├── test_duplicate_case_number_returns_409
│   ├── test_creator_auto_added_as_member
│   └── test_create_records_audit_event
├── test_case_access.py
│   ├── test_member_can_access_their_case
│   ├── test_non_member_gets_404_not_403
│   ├── test_super_admin_sees_all_cases
│   └── test_access_records_audit_event
├── test_case_members.py
│   ├── test_add_member_to_case
│   ├── test_cannot_add_duplicate_member
│   ├── test_remove_member_soft_deletes
│   ├── test_cannot_remove_last_case_officer
│   └── test_removed_member_loses_document_access
├── test_case_status.py
│   ├── test_valid_status_transitions
│   ├── test_invalid_transition_returns_409
│   ├── test_closed_case_blocks_upload
│   └── test_archived_case_blocks_all_writes
```

---

## Implementation Order

1. `departments` model + seed data (Police, Court, Forensic Lab, Legal)
2. `Case` + `CaseMember` SQLAlchemy models + migration
3. `case_schemas.py` — marshmallow schemas
4. `case_service.py` — create, get, update, access checks
5. `cases.py` Blueprint — all CRUD routes
6. `case_members.py` Blueprint — add/remove members
7. Wire access check into document service (`user_has_access`)
8. Frontend: CaseDashboard → CaseDetailPage
9. Tests
