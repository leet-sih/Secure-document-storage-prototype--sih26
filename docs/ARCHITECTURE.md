# System Architecture — Secure DMS (leet / SIH26)

> **This describes the PROTOTYPE.** Only PostgreSQL runs as a service; encrypted chunks and
> master keys live on the backend's local disk. The "Future / production" section at the bottom
> shows what returns when we scale up (MinIO, Vault, Redis, Celery, Nginx). The document-level
> data flows (chunking, integrity, audit chain) are identical either way.

## High-Level Overview (prototype)

```
┌─────────────────────────────────────────────────────────────────┐
│                          Client Browser                          │
│               React 18 + Vite (TypeScript SPA)                   │
│         Vite dev server proxies /api ──► Flask backend           │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP (localhost, dev)
                           ▼
┌──────────────────────────────────────────┐
│              Flask Backend                │
│              (Python 3.12)                │
│  ┌────────────────┐                       │
│  │  Auth Layer    │  JWT (8h) + TOTP MFA  │
│  │  RBAC guards   │                       │
│  └───────┬────────┘                       │
│  ┌───────▼────────┐                       │
│  │  Service Layer │  case · doc · audit   │
│  └───────┬────────┘                       │
│  ┌───────▼────────┐                       │
│  │  Crypto Layer  │  AES-256-GCM · HKDF   │
│  │                │  Ed25519 · SHA-256    │
│  └───┬────────┬───┘                       │
└──────┼────────┼──────────────────────────┘
       │        │              │
       ▼        ▼              ▼
┌────────────┐ ┌───────────────┐ ┌────────────────┐
│ PostgreSQL │ │ Local disk    │ │ Local file KMS │
│ (metadata) │ │ ./data/chunks │ │ ./data/keys    │
│ · users    │ │  {doc_id}/    │ │  {doc_id}.key  │
│ · cases    │ │   chunk_000n  │ │ (AES-wrapped   │
│ · documents│ │  (ciphertext) │ │  master keys)  │
│ · chunks   │ └───────────────┘ └────────────────┘
│ · audit_log│
└────────────┘
```

The three stores stay separated on purpose: the DB has only metadata, the chunk store has only
ciphertext, and the KMS has only keys — you need all three to reconstruct a document.

---

## Chunked Document Storage — Deep Dive

This is the core security innovation. Every document is split, encrypted per-chunk, and stored as
independent objects. The document can only be reconstructed with its master key.

> **Prototype ↔ production term mapping** (the flows below are identical; only the backend changes):
> "MinIO" → the **local chunk store** (`storage/chunk_store.py`, files under `./data/chunks/`).
> "Vault" → the **local file KMS** (`core/kms.py`, AES-wrapped keys under `./data/keys/`).

### Upload Flow

```
User uploads file.pdf (10 MB)
         │
         ▼
 Stream file in 1 MB chunks
         │
         ├── Chunk 0 (1 MB) ──┐
         ├── Chunk 1 (1 MB)   │
         ├── ...              │
         └── Chunk 9 (rest)   │
                              ▼
                  Generate master_key (32 bytes, random)
                  Store master_key in Vault as:
                    secret/docs/{doc_id}/master_key
                              │
                  For each chunk i:
                    ┌─────────────────────────────────┐
                    │ chunk_key = HKDF(               │
                    │   master_key,                   │
                    │   salt = doc_id,                │
                    │   info = f"chunk-{i}",          │
                    │   length = 32                   │
                    │ )                               │
                    │ iv = random_bytes(12)           │
                    │ ciphertext, auth_tag =          │
                    │   AES_256_GCM(chunk_key, iv,    │
                    │   plaintext_chunk)              │
                    │ chunk_hash = SHA256(ciphertext) │
                    └──────────────┬──────────────────┘
                                   │
                    Upload to MinIO: doc-chunks/{doc_id}/chunk_{i}
                    (ciphertext already includes the 16-byte GCM auth tag)
                    Store in DB (document_chunks):
                      - chunk_index: i
                      - minio_key: doc-chunks/{doc_id}/chunk_{i}
                      - iv: hex(iv)
                      - chunk_hash: hex(chunk_hash)   # SHA256 of ciphertext(+tag)
                              │
                  integrity_hash = SHA256(chunk_0_hash || chunk_1_hash || ...)
                  Store in DB (documents):
                    - total_chunks, integrity_hash, file_size, mime_type, etc.
                              │
                  Record AuditEvent: DOCUMENT_UPLOADED
```

### Download / Reconstruction Flow

```
User requests GET /documents/{id}/download
         │
         ▼
  Verify: user has access to parent case (RBAC check)
         │
         ▼
  Fetch master_key from Vault
         │
         ▼
  Fetch all chunk metadata from DB (ordered by chunk_index)
         │
         ▼
  running_hash_inputs = []

  PASS 1 — VERIFY EVERYTHING BEFORE SENDING ANY BYTE (prototype):
  For each chunk i (in order):
    ┌─────────────────────────────────────────────┐
    │ Fetch ciphertext from MinIO                 │
    │ Verify: SHA256(ciphertext) == chunk_hash    │ ← storage-tamper check
    │ chunk_key = HKDF(master_key, doc_id, i)    │
    │ plaintext = AES_256_GCM_DECRYPT(            │
    │   chunk_key, iv, ciphertext)                │ ← GCM tag (in ciphertext) validates
    │ running_hash_inputs.append(chunk_hash)      │
    └──────────────────┬──────────────────────────┘
                       │
  computed_integrity = SHA256(all chunk_hashes concatenated)
  If computed_integrity != stored integrity_hash  → abort 422 + AuditEvent: INTEGRITY_VIOLATION
  If any SHA256/GCM check failed                   → abort 422 + AuditEvent: INTEGRITY_VIOLATION
         │
         ▼
  PASS 2 — only now stream the reassembled plaintext to the client.
  (A tampered document therefore never produces a single downloaded byte.)
         │
         ▼
  Record AuditEvent: DOCUMENT_DOWNLOADED
```

> Trade-off: pre-verification buffers/decrypts the whole document first (fine for the prototype's
> file sizes). For very large forensic media, production switches to a two-pass streaming scheme
> that re-reads from MinIO rather than holding plaintext in RAM. See chunked_document_storage_plan.md.

---

## Audit Trail — Hash Chain

Modelled after blockchain-lite: each audit event includes the hash of the previous event, making the chain tamper-evident without requiring an external blockchain.

```
Event 1 (Genesis)
  prev_hash: "0000...0000" (64 zeros)
  payload: {type: "SYSTEM_INIT", ts: ...}
  this_hash: SHA256("0000...0000" + payload_json)

Event 2
  prev_hash: Event1.this_hash
  payload: {type: "USER_CREATED", actor: "admin", ...}
  this_hash: SHA256(Event1.this_hash + payload_json)

Event 3
  prev_hash: Event2.this_hash
  ...
```

Tampering with any event changes its hash, breaking all subsequent hashes. The `/audit/verify` endpoint recomputes the entire chain and reports any breaks.

---

## RBAC Matrix

| Endpoint                    | SUPER_ADMIN | CASE_OFFICER | INVESTIGATOR | PROSECUTOR | AUDITOR | VIEWER |
|-----------------------------|:-----------:|:------------:|:------------:|:----------:|:-------:|:------:|
| POST /users                 | ✓           |              |              |            |         |        |
| POST /cases                 | ✓           | ✓            |              |            |         |        |
| GET /cases (own)            | ✓           | ✓            | ✓            | ✓          |         |        |
| POST /cases/{id}/documents  | ✓           | ✓            |              |            |         |        |
| GET /documents/{id}/download| ✓           | ✓            | ✓            | ✓          |         | ✓(link)|
| DELETE /documents/{id}      | ✓           | ✓            |              |            |         |        |
| POST /documents/{id}/sign   | ✓           | ✓            | ✓            |            |         |        |
| GET /audit                  | ✓           |              |              |            | ✓       |        |
| GET /audit/verify           | ✓           |              |              |            | ✓       |        |

---

## Database Schema (Key Tables)

> Abbreviated for overview. The **authoritative** column-by-column schema for each table
> (with constraints, indexes, and status enums) lives in the matching `feature_plans/*_plan.md`.

```sql
-- Users
CREATE TABLE users (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email       TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  department_id UUID REFERENCES departments(id),
  role        TEXT NOT NULL CHECK (role IN ('SUPER_ADMIN','CASE_OFFICER','INVESTIGATOR','PROSECUTOR','AUDITOR','VIEWER')),
  totp_secret TEXT,                    -- encrypted at app level
  is_active   BOOLEAN DEFAULT TRUE,
  failed_logins INT DEFAULT 0,
  locked_until TIMESTAMPTZ,
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- Cases
CREATE TABLE cases (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_number TEXT UNIQUE NOT NULL,
  title       TEXT NOT NULL,
  description TEXT,
  status      TEXT DEFAULT 'OPEN',
  created_by  UUID REFERENCES users(id),
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- Documents (metadata only — no content)
CREATE TABLE documents (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id         UUID REFERENCES cases(id),
  filename        TEXT NOT NULL,
  mime_type       TEXT NOT NULL,
  file_size_bytes BIGINT NOT NULL,
  total_chunks    INT NOT NULL,
  integrity_hash  TEXT NOT NULL,       -- SHA256 of all chunk hashes
  doc_type        TEXT,                -- FIR, charge_sheet, forensic_report, etc.
  uploaded_by     UUID REFERENCES users(id),
  is_deleted      BOOLEAN DEFAULT FALSE,
  created_at      TIMESTAMPTZ DEFAULT now()
);

-- Chunks (references only — ciphertext is in MinIO)
CREATE TABLE document_chunks (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES documents(id),
  chunk_index INT NOT NULL,
  storage_key TEXT NOT NULL,           -- local file path now, object key later
  iv_hex      TEXT NOT NULL,           -- 12-byte nonce, hex-encoded
  chunk_hash  TEXT NOT NULL,           -- SHA256 of ciphertext
  size_bytes  INT NOT NULL,            -- plaintext size
  UNIQUE(document_id, chunk_index)
);
-- NOTE: no auth_tag column. Python's AESGCM appends the 16-byte GCM tag to the ciphertext,
-- so the tag lives inside the MinIO object. chunk_hash (SHA256 of the stored ciphertext,
-- tag included) is what we persist and re-check on download.

-- Audit Events (append-only)
CREATE TABLE audit_events (
  id              BIGSERIAL PRIMARY KEY,
  event_type      TEXT NOT NULL,
  actor_user_id   UUID REFERENCES users(id),
  target_type     TEXT,
  target_id       UUID,
  case_id         UUID,
  ip_address      INET,
  metadata        JSONB,               -- non-sensitive context only
  prev_hash       TEXT NOT NULL,
  this_hash       TEXT NOT NULL,
  created_at      TIMESTAMPTZ DEFAULT now()
);
-- Audit table: no UPDATE, no DELETE — enforce via Postgres row security or app constraint
```

---

## Security Threat Model (Summary)

| Threat | Mitigation |
|--------|-----------|
| Stolen DB access | DB holds only metadata; chunks are ciphertext in the chunk store; keys are in the KMS. DB alone is useless. |
| Stolen chunk store | Chunks are AES-256-GCM encrypted; keys live in the KMS, not the chunk store; each chunk needs a different derived key |
| Insider threat (admin) | Audit trail records all actions; hash chain detects retroactive tampering |
| Document tampering | GCM auth tag per chunk + overall integrity hash; any modification detected on download |
| Session hijacking | JWT + MFA required. *Prototype:* 8h token in localStorage. *Production:* 15-min access + httpOnly refresh + rotation |
| Brute force | Rate limiting (in-memory) + account lockout after 5 failures |
| SQL injection | SQLAlchemy ORM with parameterized queries only |
| XSS | No document content in browser storage. *Production:* CSP headers via Nginx |
| MITM | *Production:* TLS 1.3 + HSTS via Nginx (prototype runs on localhost HTTP) |
| Audit tampering | Hash-chained audit log; Postgres INSERT-only policy on audit_events |

---

## Future / Production Architecture

The prototype's simple parts are swapped for scalable services when we expand. The code already
isolates each behind a small interface, so these are drop-in changes, not rewrites:

| Prototype (now) | Production (later) | Swap point |
|-----------------|--------------------|-----------|
| Local disk `./data/chunks` | **MinIO / S3** object storage | `storage/chunk_store.py` |
| Local file KMS `./data/keys` | **HashiCorp Vault** | `core/kms.py` |
| 8h JWT in localStorage | 15-min access + **httpOnly refresh cookie + rotation** (Redis) | `core/security.py`, frontend auth |
| In-memory rate limiting | **Redis**-backed limiter + TOTP replay guard | `extensions.py`, `core/totp.py` |
| On-demand cleanup function | **Celery + beat** scheduled jobs (also OCR, embeddings) | `tasks/` |
| `flask run` on localhost | **Gunicorn + Nginx** (TLS, HSTS, CSP, security headers) | `Dockerfile`, `infra/` |

The document data flows (chunk → encrypt → store; fetch → verify → decrypt), the audit hash
chain, RBAC, MFA, and signatures are unchanged across both — only the storage/transport backends
differ.
