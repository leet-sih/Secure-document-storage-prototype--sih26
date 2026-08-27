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

## Product Name
**PRAMAAN — Secure Evidence Vault**

PRAMAAN is standalone. It is not positioned against or integrated with ICJS, eSakshya, CCTNS,
or any other national system. Do not make comparisons to or claims about those systems.

## Problem in One Line
Build a Secure Evidence Vault for law enforcement agencies, courts, and investigative departments to store, manage, retrieve, and share sensitive legal documents with cryptographic guarantees of integrity and access control.

## TOP PRIORITY: SECURITY
Security is the #1 constraint on every decision. When in doubt, choose the more secure option even at the cost of convenience or speed. Every feature must be threat-modelled before implementation.

Security non-negotiables:
- All documents encrypted at rest and in transit (AES-256-GCM per chunk)
- Least-privilege access model — every request re-authenticated, minimum permissions granted
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
- **Encrypted chunk storage:** two-server topology — `storage/chunk_store.py` dispatches to local (dev) or sftp (Server B demo) — *MinIO later*
- **Master-key storage:** local file KMS (`core/kms.py`), wrapped with `KMS_WRAPPING_KEY` (separate from `SECRET_KEY`) — *HashiCorp Vault later*
- **Background jobs:** none yet — cleanup is an on-demand function — *Celery + Redis later*

### Frontend
- **Framework:** React 18 (Vite, TypeScript)
- **Routing:** React Router v6 · **Styling:** Tailwind · **State:** React Context + useReducer · **HTTP:** native `fetch` via `apiFetch()`
- **Auth:** `AuthContext.tsx` + `useAuth()`; JWT access token kept in localStorage (*prototype*) — *in-memory token + httpOnly refresh cookie later*
- **Removed:** Zustand, Axios (see CHANGES.md §5)

### Security Layer
- **Encryption:** AES-256-GCM per document chunk; per-chunk keys via HKDF
- **Key storage:** local file KMS (keys never in the DB) — *Vault later*
- **Auth:** JWT access token, 8h TTL (*prototype*) — *15min access + 7d refresh rotation later*
- **MFA:** TOTP (Google Authenticator compatible)
- **Signatures:** Ed25519 digital signatures on documents
- **Audit Chain:** hash-chained, tamper-evident audit log (each entry hashes the previous; modification is detectable, not impossible)

### Deferred to production (NOT in the prototype)
- Redis (sessions/rate-limit/replay guard), MinIO (object storage), Vault (KMS),
  Celery+beat (async OCR queue + jobs), Nginx+TLS (reverse proxy), Gunicorn (WSGI server).
  See `codebase/infra/README.md` and `docs/ARCHITECTURE.md`.

### In prototype scope (Day 6)
- OCR: Tesseract (inline, no Celery) — five Indic language packs (hin, tam, tel, ben, guj)
  + English. Three-way confidence gate (DONE/LOW_CONFIDENCE/FAILED).
  See `feature_plans/ocr_plan.md`.

### Post-prototype roadmap
- Local LLM: Ollama (Mistral 7B) · Vector DB: Qdrant · Embeddings: all-MiniLM-L6-v2

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
│   │   ├── lib/          # apiFetch (native fetch wrapper), API helpers
│   │   ├── store/        # AuthContext.tsx (React Context + useReducer)
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

## Pre-Implementation Spec Requirement

Before writing any feature code, agents MUST follow this two-phase process:

**Phase 1 — Write the spec**
Create a spec file at `feature_plans/specs/<feature_name>_spec.md` covering:
- What the feature does and why (user-facing behaviour, not just "add endpoint")
- Exact files that will be created or modified (no others)
- Data model changes (new columns, tables, migrations needed)
- API contract (method, path, request schema, response schema, error codes)
- Security threat model: who can call this, what they could abuse, how it's mitigated
- Edge cases and failure modes (cross-reference `docs/EDGE_CASES.md`)
- Open questions or assumptions made

**Phase 2 — Self-review before touching code**
Re-read the spec and answer these questions explicitly in a `## Review` section appended to the same file:
1. Are there any security holes in this design?
2. Does anything contradict CLAUDE.md, `docs/SECURITY.md`, or the relevant `feature_plans/` plan?
3. Is there a simpler design that meets the same requirements?
4. Which edge cases from `docs/EDGE_CASES.md` apply and are they handled?
5. Could this break any existing feature? If yes, list the risk and mitigation.

Only proceed to implementation after the `## Review` section is written. The spec file stays in the repo permanently as documentation.

## Minimal File Footprint

Agents must keep changes strictly scoped to what the task requires:
- **Before editing any file**, confirm it is directly needed for the task. If unsure, do not touch it.
- **List every file you intend to modify** at the start of the task (derived from the spec's "exact files" list). Do not deviate from that list without stating why.
- **Do not refactor, reformat, or clean up code** in files that are incidentally read but not part of the task scope — not even whitespace or import ordering.
- **Do not touch shared config files** (`requirements.txt`, `package.json`, `docker-compose.yml`, migrations, etc.) unless the feature explicitly requires a new dependency or schema change.
- **Do not add, remove, or reorder imports** in files outside the scope list.
- **One feature = one branch's worth of changes.** If you notice an unrelated bug while implementing, note it in `docs/TODO.md` under a clearly labelled item rather than fixing it inline.

The goal is that every PR has a clean, reviewable diff with zero unintended noise — making merge conflicts rare and reviews fast.

## Coding Standards
- Python: Black formatter, Ruff linter, type hints everywhere, marshmallow schemas for all I/O
- TypeScript: Strict mode, ESLint + Prettier, no `any`; use React 18 functional components only — no class components
- Tests: pytest + pytest-flask (backend), Vitest + React Testing Library (frontend); write tests for all crypto and auth paths
- No `print()` for logging — use structured logging (`structlog`)
- Never log document content or PII — only IDs and event types
- All crypto operations in `backend/app/core/crypto.py` only — do not inline crypto elsewhere
- Use Flask application factory pattern (`create_app()`) — never use global `app` object outside of entry point

## Security Terminology (exact wording — do not use alternatives)

| Use this | Not this | Why |
|----------|----------|-----|
| "hash-chained, tamper-evident" | "blockchain-lite", "blockchain-grade", "immutable audit" | Accurate: detects tampering, does not prevent it |
| "least-privilege" | "zero-trust" | Matches the deck and our actual model |
| "cryptographically signed; legal admissibility is out of scope" | "legally valid", "court-admissible" | Legal admissibility requires certified PKI, out of scope |
| "chunk store (local disk; MinIO in production)" | "MinIO" as if it exists now | We use local disk in the prototype |
| "tamper-evident" | "immutable" | We detect; we do not prevent all tampering |

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
