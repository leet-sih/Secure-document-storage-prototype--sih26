# API Reference — Secure DMS

Base URL: `https://localhost/api/v1`

All endpoints require `Authorization: Bearer <access_token>` unless noted.

> This is a **quick-reference summary**. For full request/response schemas, validation rules,
> and edge cases, the per-feature files in `feature_plans/` are the source of truth. The only
> unauthenticated routes are `POST /auth/login`, `POST /auth/mfa/verify`, `POST /auth/refresh`
> (cookie), and the public `GET/POST /share/{token}` family.

---

## Auth

### POST /auth/login
No auth required.
```json
// Request
{ "email": "officer@ncrb.gov.in", "password": "..." }

// Response (MFA enabled)
{ "mfa_required": true, "temp_token": "..." }

// Response (MFA not yet set up — first login)
{ "access_token": "...", "expires_in": 900 }
// refresh_token set as httpOnly cookie
```

### POST /auth/mfa/verify
No auth required.
```json
// Request
{ "temp_token": "...", "totp_code": "123456" }

// Response
{ "access_token": "...", "expires_in": 900 }
```

### GET /auth/mfa/setup
Returns TOTP provisioning URI + QR code (base64 PNG).

### POST /auth/refresh
No auth header needed — reads httpOnly cookie.
Returns new `access_token`.

### POST /auth/logout
Invalidates refresh token.

---

## Users

### POST /users `[SUPER_ADMIN]`
Admin does **not** set a password. The server generates a one-time temporary password and returns
it once; the user must change it on first login. See `feature_plans/user_management_plan.md`.
```json
// Request
{
  "email": "investigator@police.gov.in",
  "full_name": "Arjun Sharma",
  "employee_id": "NCRB-2024-1042",
  "role": "INVESTIGATOR",
  "department_id": "uuid"
}

// Response 201  (temporary_password shown ONCE, never stored in plaintext)
{ "id": "uuid", "email": "...", "role": "INVESTIGATOR", "temporary_password": "Tmp!Abc123Xyz" }
```

### GET /users/me
Returns current user profile.

### POST /users/me/change-password `[all authenticated]`
`{ "current_password": "...", "new_password": "..." }` — invalidates all refresh tokens on success.

---

## Cases

### POST /cases `[SUPER_ADMIN, CASE_OFFICER]`
Note: `doc_type` belongs to **documents**, not cases. Cases carry `priority`/`category`.
```json
// Request
{
  "case_number": "FIR-2026-001",
  "title": "Case Title",
  "description": "...",
  "priority": "HIGH",
  "category": "CYBERCRIME"
}
```

### GET /cases
Returns paginated list of cases the user has access to.
Query params: `page`, `limit`, `status`, `search`

### GET /cases/{id}
Case detail + document list (metadata only).

### POST /cases/{id}/members `[SUPER_ADMIN, CASE_OFFICER]`
```json
{ "user_id": "uuid", "role": "INVESTIGATOR" }
```

---

## Documents

### POST /cases/{id}/documents `[SUPER_ADMIN, CASE_OFFICER]`
Multipart form: `file` (binary) + `doc_type` (string)
Returns document metadata (no content).

### GET /cases/{id}/documents
Returns document list with metadata. No content.

### GET /documents/{id}/download
Streams decrypted file bytes.
Sets `Content-Disposition: attachment`.

### GET /documents/{id}/preview `[PDF/image only]`
Returns server-rendered preview (PDF → PNG pages). Does not send raw bytes to client.

### DELETE /documents/{id} `[SUPER_ADMIN, CASE_OFFICER]`
Soft delete. Chunks remain for audit purposes.

### POST /documents/{id}/sign `[SUPER_ADMIN, CASE_OFFICER, INVESTIGATOR]`
Signs document integrity hash with user's Ed25519 key.
```json
// Response
{ "signature_id": "uuid", "signed_at": "...", "signer": "..." }
```

### GET /documents/{id}/signatures
Returns list of signatures with verification status.

### POST /documents/{id}/share `[SUPER_ADMIN, CASE_OFFICER]`
```json
// Request
{ "expires_in_hours": 24, "allowed_email": "prosecutor@court.gov.in" }

// Response
{ "share_url": "https://localhost/share/{token}", "expires_at": "..." }
```

---

## Search

### GET /documents/search
Query params: `q` (text), `doc_type`, `case_id`, `from_date`, `to_date`
Returns metadata only. Scoped to user's accessible cases.

---

## Audit

### GET /audit `[SUPER_ADMIN, AUDITOR]`
Query params: `page`, `limit`, `event_type`, `actor_id`, `from_date`, `to_date`

### GET /audit/cases/{id} `[SUPER_ADMIN, AUDITOR, CASE_OFFICER]`
Audit log filtered to a specific case.

### GET /audit/verify `[SUPER_ADMIN, AUDITOR]`
Re-validates the entire hash chain. Returns:
```json
{
  "total_events": 1523,
  "chain_valid": true,
  "first_break_at": null
}
```

---

## Error Responses

All errors follow:
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid credentials",
    "request_id": "uuid"
  }
}
```

| HTTP Status | Code | Meaning |
|-------------|------|---------|
| 400 | VALIDATION_ERROR | Invalid input |
| 401 | UNAUTHORIZED | Missing or invalid token (generic message — never reveal which field failed) |
| 403 | FORBIDDEN | Valid token but insufficient role, or share email gate mismatch |
| 404 | NOT_FOUND | Resource not found **or not accessible** (used instead of 403 for case scoping) |
| 409 | CONFLICT | Duplicate resource / invalid state transition |
| 410 | GONE | Share link expired, revoked, or exhausted |
| 422 | INTEGRITY_VIOLATION | Document failed integrity/tamper check |
| 423 | LOCKED | Account locked after repeated failed logins |
| 429 | RATE_LIMITED | Too many requests |
| 500 | INTERNAL_ERROR | Server error (details in server logs, not response) |

> **Access-scoping convention:** for case-scoped resources, a non-member receives **404**, not 403,
> so the API never confirms that a case/document they can't see exists.
