# Feature Plan: Secure Document Sharing

## What Is This Feature?

Document sharing allows a CASE_OFFICER or SUPER_ADMIN to generate a time-limited, single-use link that lets an external party (e.g., a prosecutor who is not a system user, or a court) download a specific document without needing an account.

This is the only mechanism by which documents can be accessed by someone without a full system account. It is tightly controlled, auditable, and always time-bounded.

---

## Why This Approach?

The alternative — adding every prosecutor or court clerk as a full system user — creates account management overhead and increases the attack surface. A share link:
- Has a short expiry (max 48 hours)
- Is scoped to exactly one document
- Is single-use (optional) or multi-use within the window
- Is immediately revocable
- Creates an audit event every time it is accessed

---

## How Share Links Work

```
1. CASE_OFFICER calls POST /documents/{id}/share
   Server generates:
     token = secrets.token_urlsafe(32)      ← 32 bytes = 256 bits of entropy
     token_hash = SHA256(token)             ← stored in DB (not the token itself)
   
   Stores in DB (document_share_links):
     document_id, token_hash, created_by, expires_at, max_uses, use_count=0

   Returns to CASE_OFFICER:
     share_url = https://dms.ncrb.gov.in/share/{token}
     (the raw token — only transmitted once)

2. External party receives the URL (via secure channel — email, Signal, etc.)

3. External party opens https://dms.ncrb.gov.in/share/{token}
   Server:
     Compute SHA256(token) → look up in document_share_links
     Check: not expired, not revoked, use_count < max_uses
     Increment use_count
     Log AuditEvent: SHARE_LINK_ACCESSED (with IP, user agent)
     Decrypt + stream document
```

Why store `token_hash` instead of `token`?
- If the DB is compromised, the attacker gets hashed tokens — useless without the original token
- Same principle as storing password hashes instead of passwords
- SHA-256 is appropriate here (not bcrypt) because tokens have 256 bits of entropy already — no need for slow hashing

---

## Database Schema

```sql
CREATE TABLE document_share_links (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    token_hash      TEXT NOT NULL UNIQUE,       -- SHA256(token), hex
    created_by      UUID NOT NULL REFERENCES users(id),
    allowed_email   TEXT,                       -- optional: restrict to one email address
    expires_at      TIMESTAMPTZ NOT NULL,
    max_uses        INTEGER NOT NULL DEFAULT 1, -- 1 = single-use; -1 = unlimited within window
    use_count       INTEGER NOT NULL DEFAULT 0,
    is_revoked      BOOLEAN NOT NULL DEFAULT FALSE,
    revoked_by      UUID REFERENCES users(id),
    revoked_at      TIMESTAMPTZ,
    note            TEXT,                       -- reason for sharing (e.g., "Shared with court")
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for fast token lookup (every share access hits this)
CREATE UNIQUE INDEX idx_share_token_hash ON document_share_links (token_hash);

-- Index for listing shares on a document
CREATE INDEX idx_share_document ON document_share_links (document_id, created_at DESC);
```

---

## API Endpoints

### POST /api/v1/documents/{id}/share `[SUPER_ADMIN, CASE_OFFICER]`

```json
// Request
{
  "expires_in_hours": 24,
  "max_uses": 3,
  "allowed_email": "prosecutor@court.gov.in",
  "note": "Shared with Additional Sessions Court for bail hearing"
}

// Response 201
{
  "share_id": "uuid",
  "share_url": "https://localhost/share/abc123xyz...",
  "expires_at": "2026-08-26T14:00:00Z",
  "max_uses": 3
}
```

Constraints:
- `expires_in_hours`: min 1, max 48
- `max_uses`: min 1, max 10; -1 for unlimited (SUPER_ADMIN only)
- `allowed_email`: if set, the share page requires the recipient to enter this email before download (email is not verified by sending — it's a simple gate to prevent accidental access)

Server behavior:
1. Verify user has access to parent case
2. Verify document is not deleted and case is not ARCHIVED
3. Generate `token = secrets.token_urlsafe(32)`
4. Compute `token_hash = SHA256(token.encode()).hexdigest()`
5. Store record
6. Record AuditEvent: DOCUMENT_SHARED with metadata `{document_id, expires_at, allowed_email}`
7. Return `share_url` with raw token — **never stored**

### GET /api/v1/documents/{id}/shares `[SUPER_ADMIN, CASE_OFFICER of case]`

Lists all share links for a document (active and expired):

```json
{
  "shares": [
    {
      "id": "uuid",
      "created_by": { "full_name": "...", "email": "..." },
      "allowed_email": "prosecutor@court.gov.in",
      "expires_at": "2026-08-26T14:00:00Z",
      "max_uses": 3,
      "use_count": 1,
      "is_revoked": false,
      "is_expired": false,
      "note": "Shared with Additional Sessions Court",
      "created_at": "..."
    }
  ]
}
```

### DELETE /api/v1/documents/{id}/shares/{share_id} `[SUPER_ADMIN, CASE_OFFICER (own)]`

Revokes a share link immediately. Sets `is_revoked=True`. Any future access attempt with this token returns 410 Gone.

Records AuditEvent: SHARE_LINK_REVOKED

---

## Share Access Endpoint (No Auth Required)

This endpoint is intentionally unauthenticated — it serves external parties without system accounts.

### GET /share/{token}

This is a frontend route — it renders a share download page.

### GET /api/v1/share/{token}/info

Returns public info about the share (no document content):
```json
{
  "filename": "FIR_001.pdf",
  "doc_type": "FIR",
  "file_size_bytes": 204800,
  "expires_at": "2026-08-26T14:00:00Z",
  "requires_email": true,    ← true if allowed_email is set
  "is_valid": true
}
```

Returns 410 if expired or revoked.
Returns 404 if token doesn't exist (same response — don't distinguish).

### POST /api/v1/share/{token}/download

```json
// Request (only needed if requires_email is true)
{ "email": "prosecutor@court.gov.in" }
```

Server:
1. Compute `token_hash = SHA256(token)`
2. Look up `document_share_links` by `token_hash`
3. Check: `is_revoked == False` → 410 if revoked
4. Check: `expires_at > now()` → 410 if expired
5. Check: `use_count < max_uses` (or `max_uses == -1`) → 410 if exhausted
6. If `allowed_email` is set: verify `request.email.lower() == allowed_email.lower()` → 403 if mismatch
7. Increment `use_count`
8. If `use_count == max_uses` after increment: mark as exhausted (not revoked — distinction for audit)
9. Decrypt and stream document (same as normal download, no Vault auth check — Vault key is fetched by service account)
10. Record AuditEvent: SHARE_LINK_ACCESSED with IP, user_agent, `{share_id, document_id}`

No JWT required for this endpoint.

---

## Rate Limiting on Share Endpoints

```python
# Aggressive rate limiting — this endpoint is public-facing
@share_bp.route("/<token>/download", methods=["POST"])
@limiter.limit("5 per hour per IP")
@limiter.limit("20 per day per IP")
def share_download(token): ...
```

This prevents brute-forcing token values (though 256-bit tokens make brute force computationally infeasible — the rate limit is an additional defense-in-depth measure).

---

## Frontend Components

| Component | Description |
|-----------|-------------|
| `ShareModal` | Opens when CASE_OFFICER clicks "Share Document"; inputs for expiry, max uses, email restriction, note; shows generated URL with copy button |
| `ShareListPanel` | On document detail page: lists active shares with use counts and revoke buttons |
| `ShareAccessPage` | Public page at `/share/{token}`: shows filename, expiry, optional email input; "Download" button |
| `ShareExpiredPage` | Shown when token is invalid/expired/revoked: "This link is no longer valid." — no other info |

### Share URL Copy UX

After generating a share link:
```
Share URL: https://dms.ncrb.gov.in/share/abc123...  [Copy]
⚠️ This URL will not be shown again. Save it before closing.
Expires: 24 hours from now (2026-08-26 14:00)
Max uses: 3
```

The share URL is only shown once — it is not stored anywhere the user can retrieve it again (the DB has only the hash).

---

## Security Considerations

1. **Token entropy** — `secrets.token_urlsafe(32)` gives 256 bits of entropy. Brute-forcing is computationally infeasible even with the 5/hour rate limit.
2. **Token in URL** — The token appears in the URL, which may be logged by the recipient's browser or server logs. Mitigation: use POST body instead of URL for sensitive scenarios. For the prototype, URL is acceptable.
3. **Email gate** — The `allowed_email` check is a convenience gate, not a security control. The recipient could share the link with anyone. Emphasize this in UI: "Restricting to an email address does not prevent forwarding."
4. **Https only** — Share links must be served over HTTPS. The Nginx config must redirect HTTP to HTTPS.
5. **No auth bypass** — The share endpoint calls the same `document_service.download()` function as the authenticated endpoint. The only difference is that the Vault key lookup uses a service account, not the user's identity.
6. **ARCHIVED case documents** — Share links should be blocked for documents in ARCHIVED cases. Existing active links for archived documents: revoke them on case archival.

---

## Edge Cases

| Scenario | Behaviour |
|----------|-----------|
| Token is valid but document was deleted after share created | 404 "Document not available" |
| Case is ARCHIVED after share was created | Access blocked; return 410 |
| `allowed_email` email casing mismatch (PROSECUTOR@Court.gov.in) | Compared case-insensitively |
| Token provided with extra characters (manipulation attempt) | SHA256 won't match — 404 |
| Share exhausted (use_count == max_uses) | 410 "This link has been used the maximum number of times" |
| Clock skew: `expires_at` is one second in the past | 410 — no grace period |
| CASE_OFFICER tries to revoke a share they didn't create | 403 — only creator or SUPER_ADMIN can revoke |
| Two simultaneous requests with same token, both at use_count=max_uses-1 | DB-level atomic increment: `UPDATE ... SET use_count = use_count + 1 WHERE use_count < max_uses RETURNING id` — one succeeds, one gets no rows → 410 |

The atomic increment race condition is handled at the DB level:
```python
result = db.session.execute(
    text("""
        UPDATE document_share_links
        SET use_count = use_count + 1
        WHERE token_hash = :hash
          AND is_revoked = FALSE
          AND expires_at > NOW()
          AND (max_uses = -1 OR use_count < max_uses)
        RETURNING id
    """),
    {"hash": token_hash}
)
if result.rowcount == 0:
    abort(410)  # expired, revoked, or exhausted
```

---

## Testing Plan

```
tests/sharing/
├── test_share_create.py
│   ├── test_case_officer_can_create_share
│   ├── test_investigator_cannot_create_share
│   ├── test_expiry_capped_at_48_hours
│   ├── test_share_creates_audit_event
│   └── test_share_url_contains_raw_token
├── test_share_access.py
│   ├── test_valid_token_streams_document
│   ├── test_expired_token_returns_410
│   ├── test_revoked_token_returns_410
│   ├── test_exhausted_token_returns_410
│   ├── test_email_gate_correct_email_passes
│   ├── test_email_gate_wrong_email_returns_403
│   ├── test_concurrent_access_respects_max_uses
│   └── test_access_creates_audit_event
├── test_share_revoke.py
│   ├── test_creator_can_revoke
│   ├── test_non_creator_cannot_revoke
│   ├── test_super_admin_can_revoke_any
│   └── test_revoke_creates_audit_event
```

---

## Implementation Order

1. `DocumentShareLink` SQLAlchemy model + migration
2. `sharing_service.py` — `create_share()`, `access_share()`, `revoke_share()`
3. `sharing.py` Blueprint — authenticated CRUD routes
4. `share_access.py` Blueprint — public `/share/{token}/*` routes (no JWT)
5. Nginx: rate limit rules on `/share/` prefix
6. Frontend: `ShareModal` + `ShareListPanel` + `ShareAccessPage`
7. Tests — especially race condition test for max_uses
