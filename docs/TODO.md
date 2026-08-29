# TODO — leet | SIH26 | PRAMAAN: Secure Evidence Vault | Deadline: 2nd September 2026

Priority levels: [P0] = must ship, [P1] = strong aim, [P2] = nice-to-have for demo
Status: [ ] todo | [~] in progress | [x] done

Build plan (6 phases matching slide 4):
  DAYS 1–2   Auth · MFA · RBAC + step-up MFA
  DAYS 3–4   Chunked crypto  ★ (two-server topology, opaque keys)
  DAY 5      Audit chain
  DAY 6      Search · OCR (prototype scope, no Celery)
  DAYS 7–8   Signatures · sharing (recipient-bound)
  DAY 9      Tamper demo · hardening · benchmarks

---

## PHASE 0 — Project Setup (Day 1, Aug 24)

- [ ] [P0] Initialize git repo with `.gitignore` (Python, Node, secrets)
- [ ] [P0] Create `.env.example` with all required vars (SECRET_KEY, KMS_WRAPPING_KEY, JWT_SECRET as three separate values)
- [ ] [P0] Write `docker-compose.yml` — **PostgreSQL only**
- [ ] [P0] Backend: Flask app factory (`create_app()`) with `/health` endpoint
- [ ] [P0] Frontend: React 18 + Vite init with TypeScript + Tailwind + React Router
- [ ] [P0] Configure Flask-Migrate (Alembic) for DB migrations
- [ ] [P0] Create `./data/chunks/` (Server B path) and `./data/keys/` (KMS, app host) — gitignored
- [ ] [P0] Set up structured logging (structlog)

---

## PHASE 1 — Auth, MFA & RBAC (Days 1–2, Aug 24–25)

- [ ] [P0] DB schema: `users`, `departments` tables + migration
- [ ] [P0] Password hashing with bcrypt (cost ≥ 12, 72-byte cap enforced in schema)
- [ ] [P0] JWT issuer: 8h access token with `mfa_at` claim (see auth_plan.md)
- [ ] [P0] `POST /auth/login` — credential validation, returns temp_token if MFA set
- [ ] [P0] `POST /auth/mfa/verify` — TOTP check, issues full access_token with mfa_at
- [ ] [P0] `POST /auth/logout` — clear client-side; log AuditEvent LOGOUT
- [ ] [P0] TOTP seed generation + QR code endpoint (`GET /auth/mfa/setup`)
- [ ] [P0] RBAC: `@require_roles` decorator in `core/rbac.py`
- [ ] [P0] Step-up MFA: `@require_recent_mfa(minutes=15)` decorator (reads mfa_at from JWT)
- [ ] [P0] `POST /auth/mfa/step-up` — verifies fresh TOTP, returns re-stamped token with mfa_at=now()
- [ ] [P0] `POST /users` — admin creates user (SUPER_ADMIN + step-up MFA)
- [ ] [P0] Rate limiting on `/auth/*` endpoints (in-memory, 5 req/min)
- [ ] [P1] Account lockout after 5 failed login attempts (15-min cooldown)
- [ ] [P1] Frontend: Login page (email/password → TOTP step)
- [ ] [P1] Frontend: MFA setup page (QR code + confirm)
- [ ] [P1] Frontend: Step-up MFA prompt (modal, triggered on MFA_REQUIRED 401)
- [ ] [P1] Frontend: User management page (admin)
- [ ] [P1] Frontend: `AuthContext.tsx` + `apiFetch()` wired into App.tsx
- [ ] [P1] User admin row actions: `PATCH /users/{id}` edit-role + deactivate — backend
      `user_service.update_user`/`deactivate_user` still stubbed; the admin table currently
      creates + lists only. Deferred from `feature_plans/specs/auth_frontend_wireup_spec.md`.

---

## PHASE 2 — Case Management (Days 2–3, Aug 25–26)

- [ ] [P0] DB schema: `cases`, `case_members` tables + migration
- [ ] [P0] `POST /cases` — create case (CASE_OFFICER+)
- [ ] [P0] `GET /cases` — list cases accessible to current user
- [ ] [P0] `GET /cases/{id}` — case detail
- [ ] [P0] `PATCH /cases/{id}` — update case status/metadata
- [ ] [P0] `POST /cases/{id}/members` — assign user to case with role
- [ ] [P0] Case access control: users only see their assigned cases (404 not 403)
- [ ] [P1] Frontend: Case list dashboard
- [ ] [P1] Frontend: Case detail view with document list

---

## PHASE 3 — Chunked Document Storage (Days 3–4, Aug 26–27) ★ CORE FEATURE

### Crypto Design
- [ ] [P0] `backend/app/core/crypto.py`: AES-256-GCM, HKDF-SHA256, SHA-256 integrity hash
- [ ] [P0] `backend/app/core/kms.py`: store_key/get_key/delete_key using KMS_WRAPPING_KEY (NOT SECRET_KEY)
- [ ] [P0] `backend/app/storage/chunk_store.py`: local backend (flat opaque keys) + sftp backend skeleton

### Chunking Pipeline (Upload)
- [ ] [P0] DB schema: `documents`, `document_chunks` tables + migration
- [ ] [P0] Upload endpoint `POST /cases/{id}/documents` (multipart, up to 500 MB):
  1. Receive file in streaming fashion
  2. Split into 1 MB chunks
  3. For each chunk: `storage_key = secrets.token_hex(16)` (opaque, flat)
  4. Derive chunk key via HKDF → encrypt AES-256-GCM → `chunk_store.put_chunk(storage_key, ciphertext)`
  5. Store chunk metadata (index, storage_key, iv_hex, chunk_hash, size_bytes) in DB
  6. Store document master key in KMS (wrapped with KMS_WRAPPING_KEY)
  7. AuditEvent: DOCUMENT_UPLOADED
- [ ] [P0] `GET /cases/{id}/documents` — list documents (metadata only)

### Reconstruction Pipeline (Download)
- [ ] [P0] Download endpoint `GET /documents/{id}/download`:
  1. Verify user has access to parent case (least-privilege RBAC)
  2. Fetch master key from local file KMS
  3. Fetch all chunk metadata from DB ordered by chunk_index (NOT storage_key)
  4. Pre-verify pass: fetch each chunk by storage_key, verify SHA256 + GCM tag, recompute integrity_hash. Abort before sending any byte on mismatch → 422 + INTEGRITY_VIOLATION
  5. Stream reassembled plaintext only after full verification
  6. AuditEvent: DOCUMENT_DOWNLOADED
- [ ] [P0] Two-server demo: configure CHUNK_STORE_BACKEND=sftp, chunk store on a separate machine with its own OS user and SSH key

### Document Management
- [ ] [P0] `DELETE /documents/{id}` — soft delete (chunks stay for audit). Requires step-up MFA.
- [ ] [P1] Document tagging: `doc_type` field (FIR, CHARGE_SHEET, etc.)
- [ ] [P1] Frontend: Document upload component (drag-and-drop, progress bar, 500 MB limit)
- [ ] [P1] Frontend: Document list with type/date filters

---

## PHASE 4 — Audit Trail (Day 5, Aug 28) ★ CRITICAL

- [ ] [P0] DB schema: `audit_events` table + migration (includes `user_agent` column)
- [ ] [P0] Migration: `REVOKE UPDATE, DELETE ON audit_events FROM dms_app_user`
- [ ] [P0] `AuditService.record()` with `pg_advisory_xact_lock` serialization
- [ ] [P0] `GET /audit` — paginated log (AUDITOR + SUPER_ADMIN)
- [ ] [P0] `GET /audit/verify` — recomputes chain, returns `{ chain_valid, first_break_at }` (names the first failing event)
- [ ] [P0] Wire `audit_service.record()` into every route
- [ ] [P1] Frontend: Audit log viewer + `ChainVerifyBadge`

---

## PHASE 5 — Search + OCR (Day 6, Aug 29)

### Search
- [ ] [P0] `GET /documents/search?q=...` — spans filename, tags, doc_type, dates, OCR text (search_text), in one query
- [ ] [P0] Results always filtered to user's accessible cases only — no exceptions
- [ ] [P1] PostgreSQL `tsvector` FTS + GIN index + trigger updating `search_vector`
- [ ] [P1] Frontend: Search bar with filter chips

### OCR (prototype scope — no Celery; see feature_plans/ocr_plan.md)
- [ ] [P1] `backend/app/core/ocr.py`: `preprocess_image()`, `run_tesseract()`, `score_confidence()`
- [ ] [P1] Run OCR inline on upload (after chunks stored) for image/scanned-PDF docs
- [ ] [P1] Write extracted text to `Document.search_text` → FTS trigger picks it up
- [ ] [P1] Three-way confidence gate: DONE (≥80%), LOW_CONFIDENCE (60–79%, flagged), FAILED (<60%)
- [ ] [P1] Language packs: eng, hin, tam, tel, ben, guj (all five Indic scripts from the deck)
- [ ] [P1] Dockerfile: add `tesseract-ocr` + all five Indic tessdata packs + `poppler-utils`
- [ ] [P1] `requirements.txt`: add pytesseract, Pillow, pdf2image, PyMuPDF, opencv-python-headless, numpy

---

## PHASE 6 — Digital Signatures & Sharing (Days 7–8, Aug 30–31)

### Signatures
- [ ] [P1] Ed25519 key pair per user (generated on first sign action; private key encrypted in KMS)
- [ ] [P1] `POST /documents/{id}/sign` — signs integrity_hash; requires step-up MFA
- [ ] [P1] `GET /documents/{id}/signatures` — list + verify signatures
- [ ] [P1] Frontend: Sign document button + signature status badge

### Sharing (recipient-bound — allowed_email REQUIRED)
- [ ] [P1] `POST /documents/{id}/share` — `allowed_email` is required (no anonymous links); requires step-up MFA
- [ ] [P1] `POST /share/{token}/download` — requires email field matching allowed_email; logs IP + user_agent
- [ ] [P1] Share link: max 48h expiry, revocable, use_count tracked atomically
- [ ] [P1] `DELETE /documents/{id}/shares/{share_id}` — revoke; AuditEvent SHARE_LINK_REVOKED
- [ ] [P1] Frontend: ShareModal (email required field) + ShareListPanel + ShareAccessPage

---

## PHASE 7 — Tamper Demo, Hardening & Benchmarks (Day 9, Sep 1)

- [ ] [P0] `backend/scripts/demo_tamper.py` — 5-step automated tamper demo (see EDGE_CASES.md §5)
- [ ] [P0] `backend/tests/test_download_tamper.py` — asserts exactly 0 bytes served on tampered download
- [ ] [P0] `backend/scripts/bench.py` — upload/download/tamper benchmarks; writes `docs/BENCHMARKS.md`
  - Sizes: 10 / 100 / 500 MB
  - Measures: wall time, encryption time, peak RSS, bytes served after tamper (must be 0)
- [ ] [P0] End-to-end smoke test: upload → download → audit log shows all events
- [ ] [P0] Demo data: 2 cases, multiple doc types, 3 user roles
- [ ] [P0] CORS: whitelist only frontend origin
- [ ] [P1] README with setup instructions and demo walkthrough
- [ ] [P1] API docs: Flask-Smorest OpenAPI — review and annotate

---

## FUTURE ROADMAP (post-hackathon — do NOT implement now)

### R1 — Production Infrastructure
- MinIO (replace local chunk store on Server B)
- HashiCorp Vault (replace local file KMS on app host → third host)
- Redis (rate limiting across workers, TOTP replay guard, session store)
- Celery + beat (background jobs: OCR queue, scheduled cleanup, embedding)
- Gunicorn + Nginx (TLS 1.3, HSTS, CSP, security headers)
- 15-min access token + 7-day httpOnly refresh cookie (replace 8h prototype token)

### R2 — Secure Session Playground (Document Summarisation)
- Isolated container per session (no persistent storage)
- Local LLM via Ollama (Mistral 7B) — no data leaves the server
- 30-minute session timeout; output not stored unless user explicitly saves

### R3 — AI-Based Document Retrieval
- Embedding pipeline: text extraction → sentence-transformers → Qdrant
- Semantic + BM25 hybrid search
- Query never logged with results — privacy by design
