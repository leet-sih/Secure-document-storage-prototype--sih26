# TODO — leet | SIH26 | Deadline: 2nd September 2026

Priority levels: [P0] = must ship, [P1] = strong aim, [P2] = nice-to-have for demo
Status: [ ] todo | [~] in progress | [x] done

---

## PHASE 0 — Project Setup (Day 1, Aug 24)

- [ ] [P0] Initialize git repo with `.gitignore` (Python, Node, secrets)
- [ ] [P0] Create `.env.example` with all required vars documented
- [ ] [P0] Write `docker-compose.yml` with: postgres, redis, minio, backend, frontend, nginx
- [ ] [P0] Backend: Flask app factory (`create_app()`) with `/health` endpoint
- [ ] [P0] Frontend: React 18 + Vite init with TypeScript + Tailwind + React Router
- [ ] [P0] Configure Flask-Migrate (Alembic) for DB migrations
- [ ] [P0] MinIO bucket setup script with lifecycle policy
- [ ] [P0] Set up structured logging (structlog) in backend

---

## PHASE 1 — Auth & User Management (Day 1–2, Aug 24–25)

- [ ] [P0] DB schema: `users`, `departments`, `roles`, `sessions` tables
- [ ] [P0] Alembic migration for Phase 1 schema
- [ ] [P0] Password hashing with bcrypt (cost factor ≥ 12)
- [ ] [P0] JWT issuer: 15-min access token + 7-day refresh (httpOnly cookie)
- [ ] [P0] `POST /auth/login` — credential validation + token pair
- [ ] [P0] `POST /auth/refresh` — rotate refresh token
- [ ] [P0] `POST /auth/logout` — invalidate refresh token in Redis
- [ ] [P0] TOTP seed generation + QR code endpoint (`GET /auth/mfa/setup`)
- [ ] [P0] TOTP verification middleware
- [ ] [P0] RBAC middleware — role guard decorator for all protected routes
- [ ] [P0] `POST /users` — admin creates user (SUPER_ADMIN only)
- [ ] [P0] Rate limiting on `/auth/*` endpoints (Redis-backed, 5 req/min)
- [ ] [P1] Account lockout after 5 failed login attempts (15-min cooldown)
- [ ] [P1] Frontend: Login page with MFA step
- [ ] [P1] Frontend: User management page (admin)

---

## PHASE 2 — Case Management (Day 2–3, Aug 25–26)

- [ ] [P0] DB schema: `cases`, `case_members` tables
- [ ] [P0] `POST /cases` — create case (CASE_OFFICER+)
- [ ] [P0] `GET /cases` — list cases accessible to current user
- [ ] [P0] `GET /cases/{id}` — case detail
- [ ] [P0] `PATCH /cases/{id}` — update case status/metadata
- [ ] [P0] `POST /cases/{id}/members` — assign user to case with role
- [ ] [P0] Case access control: users only see their assigned cases
- [ ] [P1] `GET /cases/{id}/timeline` — chronological event feed for a case
- [ ] [P1] Frontend: Case list dashboard
- [ ] [P1] Frontend: Case detail view with document list

---

## PHASE 3 — Chunked Document Storage (Day 3–4, Aug 26–27) ★ CORE FEATURE

This is the key differentiator. Implement carefully.

### Crypto Design
- [ ] [P0] `backend/app/core/crypto.py`:
  - AES-256-GCM encryption/decryption for a single chunk
  - Per-document master key generation (32 bytes, `secrets.token_bytes`)
  - Per-chunk IV generation (12 bytes random)
  - HKDF-SHA256 to derive per-chunk key from master key + chunk index
  - Document integrity tag: SHA-256 of all chunk hashes in order
- [ ] [P0] Key storage: master keys stored encrypted in Vault (or env KMS stub) — never in DB

### Chunking Pipeline (Upload)
- [ ] [P0] DB schema: `documents`, `document_chunks` tables
- [ ] [P0] Upload endpoint `POST /cases/{id}/documents` (multipart):
  1. Receive file in streaming fashion (do not buffer full file in RAM)
  2. Split into fixed-size chunks (default: 1 MB)
  3. For each chunk: derive key → encrypt (AES-256-GCM) → upload to MinIO
  4. Store chunk metadata (index, size, IV, chunk_hash, minio_key) in `document_chunks`
     — NOTE: the GCM auth tag is appended to the ciphertext by Python's `AESGCM` and stored
     inside the MinIO object, NOT as a separate DB column. See chunked_document_storage_plan.md.
  5. Store document metadata (filename, mime_type, total_chunks, integrity_hash) in `documents`
  6. Generate + store document master key in Vault
  7. Create AuditEvent: DOCUMENT_UPLOADED
- [ ] [P0] `GET /cases/{id}/documents` — list documents (metadata only, no content)

### Reconstruction Pipeline (Download)
- [ ] [P0] Download endpoint `GET /documents/{id}/download`:
  1. Verify user has access to parent case
  2. Fetch master key from Vault
  3. Fetch all chunk metadata from DB (ordered by index)
  4. **Pre-verify pass** (prototype): fetch every chunk, verify `SHA256(ciphertext)==chunk_hash`,
     decrypt (GCM auth tag validated), recompute overall integrity_hash. Abort BEFORE any byte
     is sent if anything mismatches → 422 + AuditEvent: INTEGRITY_VIOLATION.
  5. Only after full verification: stream reassembled plaintext to client.
  6. Create AuditEvent: DOCUMENT_DOWNLOADED
- [ ] [P0] Abort download if any chunk fails integrity check — never send a partial/tampered file
- [ ] [P2] (production) Two-pass streaming for very large files to avoid buffering full doc in RAM
- [ ] [P1] `GET /documents/{id}/preview` — in-browser preview (PDF/image only; server-side render to avoid sending raw bytes)

### Document Management
- [ ] [P0] `DELETE /documents/{id}` — soft delete (mark inactive; chunks stay in MinIO for audit)
- [ ] [P1] `GET /documents/{id}/versions` — version history
- [ ] [P1] Document tagging: `type` field (FIR, charge_sheet, forensic_report, etc.)
- [ ] [P1] Frontend: Document upload component (drag-and-drop, progress bar)
- [ ] [P1] Frontend: Document list with type/date filters

---

## PHASE 4 — Audit Trail (Day 4, Aug 27) ★ CRITICAL FOR COMPLIANCE

- [ ] [P0] DB schema: `audit_events` table
  - Fields: `id`, `event_type`, `actor_user_id`, `target_entity_type`, `target_entity_id`, `timestamp`, `prev_hash`, `this_hash`, `metadata_json`
  - `this_hash = SHA-256(prev_hash + event_type + actor_id + target_id + timestamp)`
  - `prev_hash` = hash of the immediately preceding event (genesis block uses zeros)
- [ ] [P0] `AuditService.record(event)` — called internally after every sensitive action
- [ ] [P0] Audit events to capture: LOGIN, LOGOUT, LOGIN_FAILED, CASE_CREATED, CASE_ACCESSED, DOCUMENT_UPLOADED, DOCUMENT_DOWNLOADED, DOCUMENT_DELETED, DOCUMENT_PREVIEWED, USER_CREATED, ROLE_CHANGED, MFA_ENABLED, UNAUTHORIZED_ACCESS_ATTEMPT
- [ ] [P0] `GET /audit` — paginated audit log (AUDITOR + SUPER_ADMIN only)
- [ ] [P0] `GET /audit/verify` — endpoint that re-validates entire hash chain (detects tampering)
- [ ] [P1] `GET /audit/cases/{id}` — audit log filtered to a case
- [ ] [P1] Frontend: Audit log viewer with filters (user, event type, date range)

---

## PHASE 5 — Search & Retrieval (Day 5, Aug 28)

- [ ] [P0] `GET /documents/search?q=...` — metadata search (filename, type, case name, date range, tags)
- [ ] [P0] Search scoped to user's accessible cases only
- [ ] [P1] Full-text search on document metadata using PostgreSQL `tsvector`
- [ ] [P1] Frontend: Search bar with filter chips

---

## PHASE 6 — Digital Signatures (Day 5–6, Aug 28–29)

- [ ] [P1] Key pair generation per user (Ed25519) stored in Vault
- [ ] [P1] `POST /documents/{id}/sign` — sign document integrity hash with user's private key
- [ ] [P1] `GET /documents/{id}/signatures` — list signatures + verify each
- [ ] [P1] Signature record in DB: `document_signatures` table
- [ ] [P1] Frontend: Sign document button + signature status badge

---

## PHASE 7 — Sharing & Collaboration (Day 6, Aug 29)

- [ ] [P1] `POST /documents/{id}/share` — generate time-limited share link (max 48h, scoped viewer token)
- [ ] [P1] Share link validates: not expired, not revoked, IP binding optional
- [ ] [P1] `DELETE /documents/{id}/share/{token}` — revoke share link
- [ ] [P1] `GET /cases/{id}/activity` — collaborative activity feed

---

## PHASE 8 — Polish & Demo Prep (Day 7–9, Aug 30 – Sep 1)

- [ ] [P0] End-to-end test: upload → view → download → audit log shows all events
- [ ] [P0] Populate demo data: 2 cases, multiple document types, 3 user roles
- [ ] [P0] Security headers: HSTS, CSP, X-Frame-Options, X-Content-Type-Options
- [ ] [P0] CORS: whitelist only frontend origin (Flask-CORS, credentials=True for cookie)
- [ ] [P0] API docs: Flask-Smorest auto-generates OpenAPI/Swagger — review and annotate
- [ ] [P1] Docker Compose: single `docker compose up` brings everything up
- [ ] [P1] Nginx TLS termination with self-signed cert
- [ ] [P1] README with setup instructions and demo walkthrough
- [ ] [P1] Presentation slides (5 min pitch)

---

## FUTURE ROADMAP (Post-hackathon, do NOT implement now)

### R1 — OCR-based Document Digitisation
- Tesseract OCR pipeline for scanned documents
- Pre-processing: deskew, denoise, binarize
- Extracted text stored as searchable metadata (not in the chunk itself)
- Confidence score gating — low-confidence OCR flagged for manual review

### R2 — Secure Session Playground (Document Summarisation)
- Isolated Docker container per session (no persistent storage)
- Local LLM via Ollama (Mistral 7B) — no data leaves the server
- Document bytes decrypted in-memory, passed to LLM context, session wiped on close
- Session timeout: 30 minutes max
- No summarisation results stored unless user explicitly saves to case notes

### R3 — Chunked Storage (Already in Phase 3 — enhance)
- Variable chunk sizing based on document type
- Chunk deduplication using convergent encryption (hash-then-encrypt)
- Cross-case deduplication for forensic images (CSAM detection integration point)
- Erasure coding (k-of-n) for fault tolerance across storage nodes

### R4 — AI-based Document Retrieval
- Embedding pipeline: text extraction → sentence-transformers → Qdrant upsert
- Semantic search endpoint: natural language query → vector similarity → ranked results
- Hybrid search: BM25 keyword + vector re-ranking
- Query is never logged with results — privacy by design
