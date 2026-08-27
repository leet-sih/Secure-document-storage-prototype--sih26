# Feature Plan: Hash-Chained Audit Trail

## What Is This Feature?

Every action performed in the system — login, document upload, download, case access, role change — is recorded as a tamper-evident audit event. These events are hash-chained: each event includes the SHA-256 hash of the previous event. If anyone modifies, deletes, or inserts a record in the middle of the chain, every subsequent hash breaks. A verification endpoint recomputes the entire chain and reports `first_break_at` — the ID of the first event where the chain fails.

This is a hash-chained, tamper-evident audit trail — detection-focused, not immutable. A sufficiently privileged attacker who rewrites all subsequent hashes after a target row would pass verification; the DB-level REVOKE closes the easy path (see §Database Schema). No external blockchain dependency; no consensus overhead.

---

## Why Is It Needed?

Legal and regulatory requirements for law enforcement document systems mandate a complete, non-repudiable record of who accessed what and when. Specifically:

- **Evidence chain integrity** — Courts need to know whether evidence was accessed only by authorized parties
- **Insider threat detection** — An officer who downloads a confidential witness statement at 2 AM is flagged
- **Non-repudiation** — Users cannot deny actions the audit trail records
- **Tamper detection** — Even a compromised DBA cannot silently alter past audit records via the app user (REVOKE UPDATE/DELETE; chain break is detected on verify)

---

## How the Hash Chain Works

```
Event #1 (Genesis / first event ever)
  prev_hash = "0000000000000000000000000000000000000000000000000000000000000000"  (64 zeros)
  payload   = serialize(event_type, actor_id, target_id, timestamp, metadata)
  this_hash = SHA256( prev_hash + payload )

Event #2
  prev_hash = Event#1.this_hash
  payload   = serialize(...)
  this_hash = SHA256( Event#2.prev_hash + Event#2.payload )

Event #3
  prev_hash = Event#2.this_hash
  this_hash = SHA256( Event#3.prev_hash + Event#3.payload )

...

Event #N
  prev_hash = Event#(N-1).this_hash
  this_hash = SHA256( ... )
```

**Tampering scenario:** If someone modifies Event #5:
- Event#5.this_hash changes
- Event#6.prev_hash no longer equals the new Event#5.this_hash
- The verification endpoint recomputes and finds the break at Event #6
- Every event from #6 onward has a mismatched prev_hash

**Deletion scenario:** If someone deletes Event #5:
- Event#6.prev_hash references a hash that no longer corresponds to Event#4
- The chain break is detected at Event #6

**Insertion scenario:** If someone inserts a fake event between #5 and #6:
- The fake event's prev_hash would need to equal Event#5.this_hash ✓
- But then Event#6.prev_hash ≠ fake_event.this_hash — chain break at #6

To forge a valid insertion, an attacker would need to recompute all subsequent hashes (N-insertion through N), which requires modifying every row — a detectable, large-scale operation on the DB.

---

## What Gets Hashed

The hash input is a deterministic serialization of the event's fields:

```python
def compute_event_hash(prev_hash: str, event: AuditEvent) -> str:
    payload = "|".join([
        prev_hash,
        event.event_type,
        str(event.actor_user_id or ""),
        str(event.target_type or ""),
        str(event.target_id or ""),
        str(event.case_id or ""),
        event.ip_address or "",
        event.created_at.isoformat(),
        json.dumps(event.metadata or {}, sort_keys=True, separators=(',', ':'))
    ])
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()
```

Key rules:
- Fields are joined with `|` (pipe) as separator — a field value containing `|` won't cause ambiguity because we include all fields in fixed order
- `None` values → empty string (consistent)
- `metadata` JSON is serialized with `sort_keys=True` for determinism
- Timestamp is in ISO 8601 format with microseconds — same format always

---

## All Audit Event Types

```python
class AuditEventType(str, Enum):
    # Authentication
    LOGIN                       = "LOGIN"
    LOGIN_FAILED                = "LOGIN_FAILED"
    LOGOUT                      = "LOGOUT"
    TOKEN_REFRESHED             = "TOKEN_REFRESHED"
    MFA_ENABLED                 = "MFA_ENABLED"
    MFA_VERIFIED                = "MFA_VERIFIED"
    MFA_STEP_UP_VERIFIED        = "MFA_STEP_UP_VERIFIED"   # fresh TOTP for sensitive action
    MFA_STEP_UP_FAILED          = "MFA_STEP_UP_FAILED"     # wrong code at step-up
    ACCOUNT_LOCKED              = "ACCOUNT_LOCKED"
    PASSWORD_CHANGED            = "PASSWORD_CHANGED"
    RATE_LIMIT_EXCEEDED         = "RATE_LIMIT_EXCEEDED"

    # User Management
    USER_CREATED                = "USER_CREATED"
    USER_DEACTIVATED            = "USER_DEACTIVATED"
    USER_ACTIVATED              = "USER_ACTIVATED"
    ROLE_CHANGED                = "ROLE_CHANGED"
    DEPARTMENT_CHANGED          = "DEPARTMENT_CHANGED"

    # Case Management
    CASE_CREATED                = "CASE_CREATED"
    CASE_ACCESSED               = "CASE_ACCESSED"
    CASE_UPDATED                = "CASE_UPDATED"
    CASE_CLOSED                 = "CASE_CLOSED"
    CASE_MEMBER_ADDED           = "CASE_MEMBER_ADDED"
    CASE_MEMBER_REMOVED         = "CASE_MEMBER_REMOVED"

    # Document
    DOCUMENT_UPLOADED           = "DOCUMENT_UPLOADED"
    DOCUMENT_DOWNLOADED         = "DOCUMENT_DOWNLOADED"
    DOCUMENT_PREVIEWED          = "DOCUMENT_PREVIEWED"
    DOCUMENT_DELETED            = "DOCUMENT_DELETED"
    DOCUMENT_RESTORED           = "DOCUMENT_RESTORED"
    DOCUMENT_SEARCH_PERFORMED   = "DOCUMENT_SEARCH_PERFORMED"

    # Signatures
    DOCUMENT_SIGNED             = "DOCUMENT_SIGNED"
    SIGNATURE_VERIFIED          = "SIGNATURE_VERIFIED"

    # Sharing
    DOCUMENT_SHARED             = "DOCUMENT_SHARED"
    SHARE_LINK_ACCESSED         = "SHARE_LINK_ACCESSED"
    SHARE_LINK_REVOKED          = "SHARE_LINK_REVOKED"
    SHARE_LINK_EXPIRED          = "SHARE_LINK_EXPIRED"

    # Security Events
    UNAUTHORIZED_ACCESS_ATTEMPT = "UNAUTHORIZED_ACCESS_ATTEMPT"
    INTEGRITY_VIOLATION         = "INTEGRITY_VIOLATION"
    SUSPICIOUS_ACTIVITY         = "SUSPICIOUS_ACTIVITY"

    # System
    SYSTEM_INIT                 = "SYSTEM_INIT"
    AUDIT_CHAIN_VERIFIED        = "AUDIT_CHAIN_VERIFIED"
    AUDIT_CHAIN_BROKEN          = "AUDIT_CHAIN_BROKEN"
```

---

## Database Schema

```sql
CREATE TABLE audit_events (
    id              BIGSERIAL PRIMARY KEY,   -- sequential integer for ordering (NOT UUID)
    event_type      TEXT NOT NULL,
    actor_user_id   UUID REFERENCES users(id),     -- NULL for system events
    target_type     TEXT,                           -- "document", "case", "user", etc.
    target_id       UUID,
    case_id         UUID,                           -- denormalized for fast case-level filtering
    ip_address      INET,
    user_agent      TEXT,                           -- captured on SHARE_LINK_ACCESSED + auth events
    metadata        JSONB,                          -- non-sensitive context only
    prev_hash       TEXT NOT NULL,                  -- 64-char hex
    this_hash       TEXT NOT NULL,                  -- 64-char hex
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Critical: make this table append-only at the DB level
-- Revoke UPDATE and DELETE from the application user
REVOKE UPDATE, DELETE ON audit_events FROM dms_app_user;

-- Index for fast querying without full scan
CREATE INDEX idx_audit_actor   ON audit_events (actor_user_id, created_at DESC);
CREATE INDEX idx_audit_case    ON audit_events (case_id, created_at DESC);
CREATE INDEX idx_audit_target  ON audit_events (target_type, target_id, created_at DESC);
CREATE INDEX idx_audit_type    ON audit_events (event_type, created_at DESC);
```

Why `BIGSERIAL` instead of UUID for `id`?
- Sequential integers give a natural, unambiguous ordering for the chain
- UUIDs are not ordered — you'd need to rely solely on `created_at` which could have ties
- Hash chain integrity depends on strict ordering; BIGSERIAL enforces it at the DB level

---

## AuditService Implementation

```python
# services/audit_service.py
import hashlib
import json
from datetime import datetime, timezone
from sqlalchemy import text
from app.models.audit_event import AuditEvent
from app.extensions import db

# Fixed 64-bit constant identifying the "audit chain" advisory lock.
AUDIT_CHAIN_LOCK_KEY = 741_852_963

class AuditService:
    """
    Append-only, hash-chained audit recorder.

    CONCURRENCY — READ THIS:
    A Python threading.Lock is NOT sufficient. In production the app runs under Gunicorn with
    multiple worker *processes* (and possibly multiple containers); an in-process lock only
    serializes threads inside one process, so two workers could read the same `last_event`,
    compute the same `prev_hash`, and FORK the chain.

    The correct cross-process guard is a PostgreSQL transaction-scoped advisory lock
    (`pg_advisory_xact_lock`). It serializes ALL audit inserts regardless of process/host and
    also covers the genesis case (zero existing rows), which `SELECT ... FOR UPDATE` does not
    (there is no row to lock yet). The lock auto-releases when the transaction commits/rolls back.
    """

    def record(
        self,
        event_type: str,
        actor_user_id=None,
        target_type=None,
        target_id=None,
        case_id=None,
        ip_address=None,
        metadata=None
    ) -> AuditEvent:
        # Serialize chain appends across ALL workers/hosts for this transaction.
        db.session.execute(text("SELECT pg_advisory_xact_lock(:k)"),
                           {"k": AUDIT_CHAIN_LOCK_KEY})

        last_event = db.session.query(AuditEvent)\
            .order_by(AuditEvent.id.desc())\
            .first()

        prev_hash = last_event.this_hash if last_event else "0" * 64
        now = datetime.now(timezone.utc)

        event = AuditEvent(
            event_type=event_type,
            actor_user_id=actor_user_id,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            case_id=str(case_id) if case_id else None,
            ip_address=ip_address,
            metadata=metadata or {},
            prev_hash=prev_hash,
            created_at=now,
            this_hash=""  # computed below
        )
        event.this_hash = self._compute_hash(prev_hash, event)

        db.session.add(event)
        db.session.commit()  # releases the advisory lock
        return event

    def _compute_hash(self, prev_hash: str, event: AuditEvent) -> str:
        payload = "|".join([
            prev_hash,
            event.event_type,
            str(event.actor_user_id or ""),
            str(event.target_type or ""),
            str(event.target_id or ""),
            str(event.case_id or ""),
            event.ip_address or "",
            event.created_at.isoformat(),
            json.dumps(event.metadata or {}, sort_keys=True, separators=(',', ':'))
        ])
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

audit_service = AuditService()  # singleton
```

**Why an advisory lock and not `SELECT ... FOR UPDATE`?**
Both stop two requests from reading the same `last_event` and computing an identical `prev_hash`
(which would fork the chain). But `FOR UPDATE` locks an *existing* row — it gives no protection for
the **genesis insert** (zero rows to lock) and is easy to get subtly wrong. `pg_advisory_xact_lock`
takes a single named lock for the whole "append to audit chain" critical section, works across
Gunicorn workers and hosts, covers the genesis case, and releases automatically at commit.

**Throughput note:** this serializes *all* audit writes to one-at-a-time. That is acceptable at
prototype/agency scale. If write volume ever becomes the bottleneck, move audit writes to a single
Celery consumer (one worker, `concurrency=1`) fed by a queue — that removes lock contention while
preserving strict ordering. Do not shard the chain.

---

## Chain Verification

```python
def verify_chain() -> dict:
    events = AuditEvent.query.order_by(AuditEvent.id.asc()).all()
    total = len(events)
    first_break = None

    expected_prev = "0" * 64

    for event in events:
        if event.prev_hash != expected_prev:
            first_break = event.id
            break

        recomputed = audit_service._compute_hash(event.prev_hash, event)
        if recomputed != event.this_hash:
            first_break = event.id
            break

        expected_prev = event.this_hash

    is_valid = first_break is None

    # Record the verification itself as an audit event
    audit_service.record(
        AuditEventType.AUDIT_CHAIN_VERIFIED if is_valid else AuditEventType.AUDIT_CHAIN_BROKEN,
        metadata={"total_events": total, "first_break_at": first_break}
    )

    return {
        "total_events": total,
        "chain_valid": is_valid,
        "first_break_at": first_break
    }
```

---

## API Endpoints

### GET /api/v1/audit
Roles: SUPER_ADMIN, AUDITOR

Query params:
- `page` (int, default 1)
- `limit` (int, default 50, max 200)
- `event_type` (string, optional filter)
- `actor_id` (UUID, optional)
- `case_id` (UUID, optional)
- `target_type` (string, optional)
- `from_date` (ISO 8601, optional)
- `to_date` (ISO 8601, optional)

Response:
```json
{
  "items": [
    {
      "id": 1523,
      "event_type": "DOCUMENT_DOWNLOADED",
      "actor": { "id": "...", "email": "officer@police.gov.in", "role": "CASE_OFFICER" },
      "target_type": "document",
      "target_id": "...",
      "case_id": "...",
      "ip_address": "192.168.1.45",
      "metadata": { "filename": "FIR_001.pdf" },
      "created_at": "2026-08-25T14:32:11.123456Z"
    }
  ],
  "total": 1523,
  "page": 1,
  "pages": 31
}
```

Note: `prev_hash` and `this_hash` are NOT included in the API response. They are internal integrity fields. The audit viewer has no business seeing them.

### GET /api/v1/audit/cases/{case_id}
Same as above, filtered to a specific case. Accessible to SUPER_ADMIN, AUDITOR, and the case's CASE_OFFICER.

### GET /api/v1/audit/verify
Roles: SUPER_ADMIN, AUDITOR

Response:
```json
{
  "total_events": 4821,
  "chain_valid": true,
  "first_break_at": null,
  "verified_at": "2026-08-25T14:35:00Z"
}
```

---

## Frontend Components

| Component | Description |
|-----------|-------------|
| `AuditLogTable` | Paginated table; columns: timestamp, event, actor, target, IP; color-coded by severity |
| `AuditFilters` | Event type dropdown, date range picker, actor search, case filter |
| `ChainVerifyBadge` | Shows "Chain Valid ✓" or "TAMPERING DETECTED ✗" after calling verify endpoint |
| `EventDetailModal` | Expand a row to see full metadata JSON |

Severity colour coding:
- Green: LOGIN, DOCUMENT_UPLOADED, CASE_CREATED
- Yellow: DOCUMENT_DOWNLOADED, DOCUMENT_SHARED, CASE_ACCESSED
- Orange: DOCUMENT_DELETED, ROLE_CHANGED, ACCOUNT_LOCKED
- Red: UNAUTHORIZED_ACCESS_ATTEMPT, INTEGRITY_VIOLATION, AUDIT_CHAIN_BROKEN, LOGIN_FAILED

---

## Where `audit_service.record()` Is Called

Every route handler or service function that performs a sensitive action must call `audit_service.record()` before returning. This is not optional.

Pattern to follow:
```python
@documents_bp.route("/<uuid:doc_id>/download", methods=["GET"])
@jwt_required()
@require_roles(Role.CASE_OFFICER, Role.INVESTIGATOR, Role.SUPER_ADMIN)
def download_document(doc_id, current_user):
    # ... do the work ...
    document = document_service.download(doc_id, current_user.id)

    audit_service.record(
        AuditEventType.DOCUMENT_DOWNLOADED,
        actor_user_id=current_user.id,
        target_type="document",
        target_id=doc_id,
        case_id=document.case_id,
        ip_address=request.remote_addr,
        metadata={"filename": document.filename}
    )

    return send_file(...)
```

**Never** call `audit_service.record()` inside the service layer — call it at the route layer. The service layer is responsible for the operation; the route layer is responsible for recording it. This keeps audit calls explicit and visible.

---

## Edge Cases

| Scenario | Behaviour |
|----------|-----------|
| Database write fails mid-upload, so audit event isn't recorded | The upload itself fails — partial state is cleaned up. No audit event needed for a failed operation except in the error handler (DOCUMENT_UPLOAD_FAILED). |
| Two concurrent downloads trigger simultaneous audit records | `pg_advisory_xact_lock` serializes chain appends across all workers/hosts — both events recorded correctly, in order (a Python `threading.Lock` would NOT — it only covers one process). |
| Audit table grows very large (years of data) | Partition by month using PostgreSQL table partitioning. Each partition is independently verifiable. Genesis hash of partition N is the last hash of partition N-1. |
| Admin tries to delete an audit row directly in DB | `REVOKE DELETE ON audit_events FROM dms_app_user` prevents this at the DB level. They'd need `postgres` superuser — which should be monitored by the OS. |
| System crash between hash computation and DB commit | Transaction rolls back, the event is not recorded. No partial write. |

---

## Performance

Audit events are high-frequency writes. Optimizations:
- Fetching `last_event` is fast because `id DESC` uses the primary key — one row lookup. The advisory lock is an in-memory Postgres lock (no table I/O).
- Consider a write-ahead log approach: buffer audit events in Redis and flush to DB in batches via Celery (for very high write volumes). Not needed for prototype.
- `BIGSERIAL` primary key means inserts are append-only — no B-tree rebalancing in hot paths.
- Read queries use covering indexes — no table scans for filtered views.

---

## Testing Plan

```
tests/audit/
├── test_audit_record.py
│   ├── test_first_event_has_genesis_prev_hash
│   ├── test_sequential_events_form_valid_chain
│   ├── test_concurrent_events_dont_fork_chain
│   ├── test_event_contains_correct_actor_and_target
│   └── test_event_metadata_is_stored
├── test_audit_verify.py
│   ├── test_verify_returns_valid_for_untampered_chain
│   ├── test_verify_detects_modified_event_type
│   ├── test_verify_detects_modified_metadata
│   ├── test_verify_detects_deleted_event
│   ├── test_verify_detects_inserted_event
│   ├── test_verify_reports_correct_break_point
│   └── test_verify_itself_creates_audit_event
├── test_audit_api.py
│   ├── test_audit_list_requires_auditor_role
│   ├── test_audit_list_filters_by_event_type
│   ├── test_audit_list_filters_by_date_range
│   ├── test_audit_list_filters_by_case_id
│   └── test_audit_response_does_not_include_hashes
```

---

## Implementation Order

1. `AuditEvent` SQLAlchemy model + migration
2. `AuditService` with `record()` and `_compute_hash()` and `verify_chain()`
3. DB-level REVOKE on audit_events table (add to migration)
4. `audit_schemas.py` — marshmallow serialization schema
5. `audit.py` Blueprint — `GET /audit`, `GET /audit/cases/<id>`, `GET /audit/verify`
6. Wire `audit_service.record()` into every route (auth, cases, documents)
7. Frontend: `AuditLogTable` + `AuditFilters` + `ChainVerifyBadge`
8. Tests
