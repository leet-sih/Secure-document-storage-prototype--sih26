# CLAUDE.md — Project Instructions for All Agents

## Project Identity
- **Team:** leet (6 members)
- **Competition:** Smart India Hackathon (SIH) 2026
- **Problem Statement ID:** 26190
- **Organization:** Ministry of Home Affairs / NCRB
- **Prototype Deadline:** 2nd September 2026
- **Working Directory:** `C:\Users\aarja\Desktop\SIH26\codebase`

## Feature Plans & Key Docs
Detailed per-feature plans live in `feature_plans/`. Start here before implementing any feature.
See `feature_plans/contents.md` for the full index.
- `docs/ARCHITECTURE.md` — system overview + data flows (abbreviated schemas)
- `docs/SECURITY.md` — crypto standards, env vars, RBAC, rate limits, PR checklist
- `docs/API.md` — endpoint quick-reference
- `docs/EDGE_CASES.md` — **cross-cutting failure modes + the pre-demo smoke test. Read before shipping any feature.**
- `docs/TODO.md` — phased task list to Sep 2

The per-feature plans and `feature_plans/audit_trail_plan.md`'s `AuditEventType` enum are the
**single source of truth**; the summaries in `docs/` are abbreviated and point back to them.

## Problem in One Line
Build a Secure Digital Document Management System (DMS) for law enforcement agencies, courts, and investigative departments to store, manage, retrieve, and share sensitive legal documents.

## TOP PRIORITY: SECURITY
Security is the #1 constraint on every decision. When in doubt, choose the more secure option even at the cost of convenience or speed. Every feature must be threat-modelled before implementation.

Security non-negotiables:
- All documents encrypted at rest and in transit (AES-256-GCM per chunk)
- Zero-trust access model — every request re-authenticated
- Complete, tamper-evident audit trail for every document action
- No plaintext document ever touches disk unencrypted
- RBAC enforced at API layer, not just UI
- No secrets in code — all via environment variables
- Input validation and sanitization at every boundary
- SQL parameterized queries only — no raw string interpolation
- Rate limiting on auth/sensitive endpoints (in-memory in the prototype)
- CORS locked to the frontend origin (CSP/HSTS security headers return with Nginx in production)

## Tech Stack

> **We are building the PROTOTYPE first** — simplest thing that works, so 6 people can move
> fast. The security *mechanisms* stay (chunked encryption, integrity checks, audit hash-chain,
> RBAC, MFA, signatures); the heavy *infrastructure* around them is deferred. "Later / production"
> items below come back when we expand — the code isolates them behind small interfaces.

### Backend
- **Runtime:** Python 3.12 + Flask 3.x
- **Flask extensions:** Flask-SQLAlchemy, Flask-Migrate (Alembic), Flask-JWT-Extended, Flask-Limiter (in-memory), Flask-Smorest (OpenAPI docs)
- **Validation:** marshmallow (`unknown=RAISE`)
- **Database:** PostgreSQL 16 (metadata, users, audit logs, case registry)
- **Encrypted chunk storage:** local filesystem (`storage/chunk_store.py`) — *MinIO later*
- **Master-key storage:** local file KMS (`core/kms.py`) — *HashiCorp Vault later*
- **Background jobs:** none yet — cleanup is an on-demand function — *Celery + Redis later*

### Frontend
- **Framework:** React 18 (Vite, TypeScript)
- **Routing:** React Router v6 · **Styling:** Tailwind · **State:** Zustand · **HTTP:** Axios
- **Auth:** custom hooks; JWT access token kept in localStorage (*prototype*) — *in-memory token + httpOnly refresh cookie later*

### Security Layer
- **Encryption:** AES-256-GCM per document chunk; per-chunk keys via HKDF
- **Key storage:** local file KMS (keys never in the DB) — *Vault later*
- **Auth:** JWT access token, 8h TTL (*prototype*) — *15min access + 7d refresh rotation later*
- **MFA:** TOTP (Google Authenticator compatible)
- **Signatures:** Ed25519 digital signatures on documents
- **Audit Chain:** hash-chained audit log (each entry hashes the previous — blockchain-lite)

### Deferred to production (NOT in the prototype)
- Redis (sessions/rate-limit/replay guard), MinIO (object storage), Vault (KMS),
  Celery+beat (async jobs), Nginx+TLS (reverse proxy), Gunicorn (WSGI server).
  See `codebase/infra/README.md` and `docs/ARCHITECTURE.md`.

### Future AI/ML (post-prototype roadmap)
- OCR: Tesseract · Local LLM: Ollama (Mistral 7B) · Vector DB: Qdrant · Embeddings: all-MiniLM-L6-v2

## Codebase Structure

```
codebase/
├── backend/
│   ├── app/
│   │   ├── __init__.py   # create_app() factory
│   │   ├── blueprints/   # Flask Blueprints (auth, cases, documents, audit, users)
│   │   ├── core/         # Config, security utils, crypto primitives, extensions init
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # marshmallow schemas (validation + serialization)
│   │   ├── services/     # Business logic (document, case, user, audit)
│   │   ├── storage/      # chunk_store.py — encrypted chunks on local disk (prototype)
│   │   └── tasks/        # maintenance.py — on-demand cleanup (no Celery yet)
│   ├── migrations/       # Flask-Migrate (Alembic) migration files
│   ├── tests/
│   ├── Dockerfile
│   ├── wsgi.py           # exports `app` from create_app()
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── pages/        # Route-level page components (React Router)
│   │   ├── components/   # Reusable UI components
│   │   ├── hooks/        # Custom hooks (useAuth, useCase, useDocument)
│   │   ├── lib/          # Axios client, API helpers
│   │   ├── store/        # Zustand stores (auth, ui)
│   │   └── types/        # Shared TypeScript interfaces
│   ├── Dockerfile
│   ├── vite.config.ts
│   └── package.json
├── infra/
│   ├── docker-compose.yml   # PostgreSQL only (backend/frontend run locally)
│   └── README.md            # prototype vs. future infrastructure
├── docs/
│   ├── ARCHITECTURE.md
│   ├── SECURITY.md
│   ├── EDGE_CASES.md
│   ├── TODO.md
│   └── API.md
├── feature_plans/          # per-feature deep-dives (source of truth)
└── CLAUDE.md
```

## Roles in the System (RBAC)
| Role | Description |
|------|-------------|
| `SUPER_ADMIN` | System admin — manage users, view all audit logs |
| `CASE_OFFICER` | Create/manage cases, upload documents |
| `INVESTIGATOR` | View + annotate assigned case documents |
| `PROSECUTOR` | Read-only access to case files (court-shared) |
| `AUDITOR` | Read-only access to audit logs |
| `VIEWER` | Scoped read-only (single document, time-limited link) |

## Key Domain Entities
- **Case** — the root container; every document belongs to a case
- **Document** — metadata record; actual bytes live as encrypted chunks in MinIO
- **Chunk** — encrypted binary fragment of a document; each has its own IV/nonce
- **AuditEvent** — immutable record of every action; hash-chained
- **User** — belongs to a department; has a role
- **Department** — police station, court, forensic lab, etc.

## Coding Standards
- Python: Black formatter, Ruff linter, type hints everywhere, marshmallow schemas for all I/O
- TypeScript: Strict mode, ESLint + Prettier, no `any`; use React 18 functional components only — no class components
- Tests: pytest + pytest-flask (backend), Vitest + React Testing Library (frontend); write tests for all crypto and auth paths
- No `print()` for logging — use structured logging (`structlog`)
- Never log document content or PII — only IDs and event types
- All crypto operations in `backend/app/core/crypto.py` only — do not inline crypto elsewhere
- Use Flask application factory pattern (`create_app()`) — never use global `app` object outside of entry point

## What Agents Should NOT Do
- Do not use `request.json` directly — always load through a marshmallow schema (`unknown=RAISE`)
- Do not store any document content in PostgreSQL rows — only metadata + chunk references
- Do not store document master keys, TOTP secrets, or signing keys in the DB in plaintext (Vault/KMS or app-encrypted only)
- Do not return **403** for a case-scoped resource a user can't see — return **404** (don't confirm it exists)
- Do not guard the audit hash-chain with a Python `threading.Lock` — it does not hold across Gunicorn workers; use `pg_advisory_xact_lock`
- Do not reuse one AES key across chunks — every chunk gets its own HKDF-derived key (keeps random GCM IVs safe)
- Do not let bcrypt silently truncate — cap passwords at 72 bytes (or pre-hash)
- Do not add `console.log` with sensitive data
- Do not bypass auth middleware for "testing convenience"
- Do not commit `.env` files — use `.env.example` with placeholder values
- Do not use MD5 or SHA-1 for anything security-related
- Do not use ECB mode for any encryption
- Do not use the async `asyncpg` driver — Flask is synchronous (`postgresql+psycopg`)
