# System Architecture — PRAMAAN: Secure Evidence Vault (leet / SIH26)

> **This describes the PROTOTYPE.** The two-server separation (Server A = metadata,
> Server B = ciphertext) is the key architectural claim from the deck. The "Future / production"
> section at the bottom shows what replaces the remaining stubs (MinIO, Vault, Redis, Celery,
> Nginx). The document-level data flows (chunking, integrity, audit chain) are identical
> across prototype and production.

---

## High-Level Overview (prototype — two-server topology)

```
┌─────────────────────────────────────────────────────────────────┐
│                          Client Browser                          │
│        React 18 + Vite (TypeScript SPA)                         │
│        State: React Context + useReducer                        │
│        HTTP: native fetch via apiFetch()  (no Axios)            │
│        Vite dev server proxies /api ──► Flask backend            │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP (localhost dev / HTTPS production)
                           ▼
┌───────────────────────────────────────────────────────────────────┐
│                       Flask Backend (app host)                    │
│                          (Python 3.12)                            │
│  ┌─────────────────┐                                              │
│  │  Auth Layer     │  JWT (8h) + TOTP MFA at login               │
│  │  RBAC guards    │  + @require_recent_mfa on sensitive actions  │
│  └────────┬────────┘                                              │
│  ┌────────▼────────┐                                              │
│  │  Service Layer  │  case · doc · audit · search · share        │
│  └────────┬────────┘                                              │
│  ┌────────▼────────┐                                              │
│  │  Crypto Layer   │  AES-256-GCM · HKDF · Ed25519 · SHA-256    │
│  └───┬─────────┬───┘                                              │
│      │         │         │                                        │
│      │         │   ┌─────▼──────────────────────────────────┐    │
│      │         │   │  Local file KMS (./data/keys)          │    │
│      │         │   │  AES-wrapped with KMS_WRAPPING_KEY     │    │
│      │         │   │  (separate secret from SECRET_KEY)     │    │
│      │         │   └────────────────────────────────────────┘    │
└──────┼─────────┼──────────────────────────────────────────────────┘
       │         │
       ▼         ▼
┌──────────────┐   ┌────────────────────────────────────────┐
│  SERVER A    │   │  SERVER B                              │
│  PostgreSQL  │   │  Chunk store (local disk prototype)    │
│  (metadata)  │   │  Path: ./data/chunks/{opaque_key}      │
│  · users     │   │  OPAQUE flat namespace — no doc IDs,   │
│  · cases     │   │  no chunk indexes in filenames.        │
│  · documents │   │  Ciphertext only. No keys. No DB.      │
│  · chunks    │   │                                        │
│  · audit_log │   │  In demo: separate physical machine.   │
└──────────────┘   │  Access: sftp, key auth, dedicated OS  │
                   │  user. No password. App only.          │
                   └────────────────────────────────────────┘
```

**Why two servers?** Compromising Server A (metadata) alone gives an attacker chunk
storage keys (opaque random strings) but no ciphertext. Compromising Server B (ciphertext)
alone gives unreadable blobs — no structure, no keys. Both must be compromised simultaneously
with the KMS to reconstruct any document.

---

## KMS Boundary Decision

**Prototype choice (option b — honest middle ground):**
- KMS lives on the app host under a dedicated OS user.
- Master keys are AES-wrapped with `KMS_WRAPPING_KEY` — a **separate** env var from `SECRET_KEY`.
  `SECRET_KEY` handles Flask session signing only. Two different jobs, two different secrets.
- Server B (chunk store) has no key material.
- Server A (database) has no key material.

**Production (option a):** KMS moves to a third host running HashiCorp Vault. Same
`core/kms.py` interface — only the backend swaps.

See `docs/SECURITY.md` "Key lifecycle" for generation, rotation, backup, and compromise response.

---

## Chunked Document Storage — Deep Dive

This is the core security innovation. Every document is split, encrypted per-chunk with an
opaque storage key, and stored as independent objects. The document can only be reconstructed
with its master key.

### Upload Flow

```
User uploads file.pdf (up to 500 MB)
         │
         ▼
 Stream file in 1 MB chunks
         │
         ├── Chunk 0 (1 MB) ──┐
         ├── Chunk 1 (1 MB)   │
         └── Chunk n (rest)   │
                              ▼
                  Generate master_key (32 bytes, random)
                  Store master_key in local file KMS:
                    KMS_DIR/{doc_id}.key  (AES-wrapped, KMS_WRAPPING_KEY)
                              │
                  For each chunk i:
                    ┌─────────────────────────────────────┐
                    │ storage_key = secrets.token_hex(16) │ ← opaque, generated here
                    │ chunk_key = HKDF(                   │
                    │   master_key,                       │
                    │   salt = doc_id,                    │
                    │   info = f"chunk-{i}",              │
                    │   length = 32                       │
                    │ )                                   │
                    │ iv = random_bytes(12)               │
                    │ ciphertext = AES_256_GCM(           │
                    │   chunk_key, iv, plaintext_chunk)   │
                    │ chunk_hash = SHA256(ciphertext)     │
                    └──────────────┬──────────────────────┘
                                   │
                    chunk_store.put_chunk(storage_key, ciphertext)
                    → flat file at CHUNK_STORAGE_DIR/{storage_key}
                    Store in DB (document_chunks):
                      - chunk_index: i
                      - storage_key: opaque random string
                      - iv_hex: hex(iv)
                      - chunk_hash: hex(chunk_hash)
                              │
                  integrity_hash = SHA256(chunk_0_hash || chunk_1_hash || ...)
                  Store in DB (documents): integrity_hash, total_chunks, …
                              │
                  Record AuditEvent: DOCUMENT_UPLOADED
```

### Download / Reconstruction Flow

```
User requests GET /documents/{id}/download
         │
         ▼
  Verify: user has access to parent case (least-privilege RBAC check)
         │
         ▼
  Fetch master_key from local file KMS
         │
         ▼
  Fetch all chunk metadata from DB (ordered by chunk_index — NOT by storage_key)
         │
         ▼
  PASS 1 — VERIFY EVERYTHING BEFORE SENDING ANY BYTE (prototype):
  For each chunk i (in order):
    ┌─────────────────────────────────────────────┐
    │ Fetch ciphertext from chunk store by        │
    │   storage_key (opaque)                      │
    │ Verify: SHA256(ciphertext) == chunk_hash    │ ← storage-tamper check
    │ chunk_key = HKDF(master_key, doc_id, i)    │
    │ plaintext = AES_256_GCM_DECRYPT(            │
    │   chunk_key, iv, ciphertext)                │ ← GCM tag validates
    └──────────────────┬──────────────────────────┘
                       │
  computed_integrity = SHA256(all chunk_hashes concatenated)
  If computed_integrity != stored integrity_hash  → 422 + AuditEvent: INTEGRITY_VIOLATION
  If any SHA256/GCM check failed                   → 422 + AuditEvent: INTEGRITY_VIOLATION
         │
         ▼
  PASS 2 — only now stream the reassembled plaintext to the client.
  A tampered document therefore never produces a single downloaded byte.
         │
         ▼
  Record AuditEvent: DOCUMENT_DOWNLOADED
```

> Trade-off: pre-verification buffers/decrypts the whole document in RAM. At 500 MB this
> requires ~500 MB headroom on the app server. Confirmed acceptable for the prototype demo
> (see bench.py benchmarks). Production switches to two-pass streaming to avoid the RAM spike.

---

## Audit Trail — Hash Chain (tamper-evident)

Each audit event includes the hash of the previous event, making the chain tamper-evident:
if anyone modifies, deletes, or inserts a record, every subsequent hash breaks.

```
Event 1 (Genesis)
  prev_hash: "0000...0000" (64 zeros)
  payload: {type: "SYSTEM_INIT", ts: ...}
  this_hash: SHA256("0000...0000" + payload_json)

Event 2
  prev_hash: Event1.this_hash
  this_hash: SHA256(Event1.this_hash + payload_json)
...
```

`/audit/verify` recomputes the entire chain and returns `first_break_at` — the ID of the
first event where the chain fails. A null `first_break_at` means the chain is intact.
The verification itself is recorded as an audit event.

**Claim:** tamper-evident hash chain — *detection*, not immutability. A sufficiently
privileged attacker who can rewrite all subsequent hashes after a target row would pass
verification. The DB-level `REVOKE UPDATE, DELETE ON audit_events FROM dms_app_user` closes
the easy path; a full chain rewrite requires `postgres` superuser, which should be OS-monitored.

---

## Step-Up MFA

Sensitive actions require a TOTP re-check if the session's last MFA verification is older
than `MFA_STEP_UP_MINUTES` (default 15). The JWT carries an `mfa_at` (epoch) claim.

```
@require_recent_mfa(minutes=15)  ← wraps the route handler
  If now - mfa_at > 900s:
    return 401 { "code": "MFA_REQUIRED" }
    (frontend prompts for fresh TOTP code, not a full re-login)

POST /auth/mfa/step-up
  Body: { "totp_code": "123456" }
  Response: { "access_token": "<re-stamped JWT with fresh mfa_at>" }
```

Sensitive action set: sign a document, create a share link, delete a document,
create/deactivate a user, change a role.

---

## RBAC Matrix

| Endpoint                         | SUPER_ADMIN | CASE_OFFICER | INVESTIGATOR | PROSECUTOR | AUDITOR | VIEWER |
|----------------------------------|:-----------:|:------------:|:------------:|:----------:|:-------:|:------:|
| POST /users                      | ✓ (step-up) |              |              |            |         |        |
| PATCH /users/{id}/role           | ✓ (step-up) |              |              |            |         |        |
| POST /cases                      | ✓           | ✓            |              |            |         |        |
| GET /cases (own)                 | ✓           | ✓            | ✓            | ✓          |         |        |
| POST /cases/{id}/documents       | ✓           | ✓            |              |            |         |        |
| GET /documents/{id}/download     | ✓           | ✓            | ✓            | ✓          |         | ✓(link)|
| DELETE /documents/{id}           | ✓ (step-up) | ✓ (step-up)  |              |            |         |        |
| POST /documents/{id}/sign        | ✓ (step-up) | ✓ (step-up)  | ✓ (step-up)  |            |         |        |
| POST /documents/{id}/share       | ✓ (step-up) | ✓ (step-up)  |              |            |         |        |
| GET /audit                       | ✓           |              |              |            | ✓       |        |
| GET /audit/verify                | ✓           |              |              |            | ✓       |        |

*(step-up) = `@require_recent_mfa(minutes=15)` applied*

---

## Database Schema (Key Tables)

> Abbreviated for overview. Authoritative column-by-column schema (constraints, indexes,
> status enums) lives in the matching `feature_plans/*_plan.md`.

```sql
-- Documents (metadata only — no content)
CREATE TABLE documents (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id         UUID REFERENCES cases(id),
  filename        TEXT NOT NULL,
  mime_type       TEXT NOT NULL,
  file_size_bytes BIGINT NOT NULL,
  total_chunks    INT NOT NULL,
  integrity_hash  TEXT NOT NULL,
  doc_type        TEXT,
  ocr_status      TEXT DEFAULT 'NOT_APPLICABLE',
  ocr_confidence  FLOAT,
  ocr_language    TEXT DEFAULT 'eng+hin',
  ocr_page_count  INT,
  search_text     TEXT,
  search_vector   TSVECTOR,
  uploaded_by     UUID REFERENCES users(id),
  is_deleted      BOOLEAN DEFAULT FALSE,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- Chunks (opaque storage keys — ciphertext is in the chunk store, not here)
CREATE TABLE document_chunks (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES documents(id),
  chunk_index INT NOT NULL,
  storage_key TEXT NOT NULL,           -- opaque random key (secrets.token_hex(16))
  iv_hex      TEXT NOT NULL,           -- 12-byte nonce, hex
  chunk_hash  TEXT NOT NULL,           -- SHA256(ciphertext incl. GCM tag)
  size_bytes  INT NOT NULL,
  UNIQUE(document_id, chunk_index)
);
-- Note: ordering is in chunk_index only — storage_key has no structure.

-- Audit Events (append-only at DB level)
CREATE TABLE audit_events (
  id              BIGSERIAL PRIMARY KEY,
  event_type      TEXT NOT NULL,
  actor_user_id   UUID REFERENCES users(id),
  target_type     TEXT,
  target_id       UUID,
  case_id         UUID,
  ip_address      INET,
  user_agent      TEXT,
  metadata        JSONB,
  prev_hash       TEXT NOT NULL,
  this_hash       TEXT NOT NULL,
  created_at      TIMESTAMPTZ DEFAULT now()
);
REVOKE UPDATE, DELETE ON audit_events FROM dms_app_user;  -- in migration
```

---

## Security Threat Model

See `docs/THREAT_MODEL.md` for the full three-column table (defended / partially addressed /
out of scope) matching the slide-4 claim.

Short summary:
| Threat | Mitigation |
|--------|-----------|
| Server A (metadata) compromised alone | Chunk ordering is opaque storage keys — no document content, no keys |
| Server B (chunk store) compromised alone | Ciphertext only; no keys, no DB, no structure in filenames |
| DBA reading evidence content | DB has only metadata; content is AES-256-GCM encrypted in chunk store |
| Stolen credentials without second factor | TOTP required at login + step-up before sensitive actions |
| Audit trail retroactive edit | REVOKE UPDATE/DELETE at DB; hash chain detects any remaining tampering |
| Document modification in chunk store | GCM auth tag + SHA256 chunk_hash; integrity_hash; all verified before serving |

---

## Future / Production Architecture

| Prototype (now) | Production (later) | Swap point |
|-----------------|--------------------|-----------|
| Local disk chunk store (Server B via sftp) | **MinIO / S3** object storage | `storage/chunk_store.py` |
| Local file KMS (app host) | **HashiCorp Vault** (third host) | `core/kms.py` |
| 8h JWT in localStorage | 15-min access + **httpOnly refresh cookie** (Redis) | `core/security.py`, frontend auth |
| In-memory rate limiting | **Redis**-backed limiter + TOTP replay guard | `extensions.py` |
| OCR inline on upload | **Background worker** (Celery + beat) | `tasks/` |
| `flask run` on localhost | **Gunicorn + Nginx** (TLS, HSTS, CSP) | `Dockerfile`, `infra/` |
