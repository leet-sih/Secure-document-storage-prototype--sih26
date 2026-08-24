# Secure Digital Document Management System

Team **leet** · SIH 2026 · Problem Statement **26190** · Ministry of Home Affairs / NCRB

A secure, centralized DMS for law enforcement, courts, and investigative departments to store,
manage, retrieve, and share sensitive legal documents. Documents are **chunked and per-chunk
AES-256-GCM encrypted**, with the master key stored separately from the database — so no single
breached component can reconstruct a document.

> **This is the PROTOTYPE build** — deliberately kept simple so the team can move fast. Only
> PostgreSQL runs as a service; encrypted chunks and keys live on local disk. Redis, MinIO,
> Vault, Celery, and Nginx are **deferred to the production phase** (`infra/README.md`). The
> security *mechanisms* (chunked encryption, integrity checks, audit hash-chain, RBAC, MFA,
> signatures) are all still here — only the surrounding infrastructure is simplified.

---

## Repository Layout

```
codebase/
├── backend/     Flask 3 API (Python 3.12) — auth, cases, documents, audit, crypto
├── frontend/    React 18 + Vite SPA (TypeScript) — the browser UI
├── infra/       docker-compose (PostgreSQL) + README
├── .env.example Copy to .env and fill in
├── STRUCTURE.md · DEFINITIONS.md
└── README.md
```

Design docs live one level up in `../docs/` and `../feature_plans/`. **Read `../CLAUDE.md` and
your feature's `../feature_plans/<feature>_plan.md` before writing code.**

New to a term, library, or pattern used here? See **`DEFINITIONS.md`** — a plain-English
glossary with examples tied to these files. `STRUCTURE.md` is the file-by-file map.

---

## Quick Start

```bash
cp .env.example .env          # then edit .env (generate the two CHANGE_ME secrets)

# 1. Database (only service you need)
docker compose -f infra/docker-compose.yml up postgres

# 2. Backend  (new terminal)
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
flask db upgrade
python seed.py                # demo users/cases/documents
flask run --debug            # http://localhost:5000

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev                   # http://localhost:5173  (proxies /api to the backend)
```

Full step-by-step onboarding + Git workflow: **`../SETUP.md`**.

---

## Who Owns What (6-person split — adjust as needed)

| Area | Files | Feature plan |
|------|-------|--------------|
| Auth & Users | `backend/app/blueprints/{auth,users}.py`, `services/{auth,user}_service.py`, `core/{security,totp,rbac}.py` | auth_plan, user_management_plan |
| Crypto & Chunked Storage | `core/{crypto,kms,signing}.py`, `storage/chunk_store.py`, `services/document_service.py` | chunked_document_storage_plan |
| Cases & Search | `services/{case,search}_service.py`, `blueprints/{cases,search}.py` | case_management_plan, search_plan |
| Audit & Signatures | `services/{audit,signature}_service.py`, `blueprints/{audit,signatures}.py` | audit_trail_plan, digital_signatures_plan |
| Sharing & Infra | `blueprints/{sharing,share_access}.py`, `infra/*` | document_sharing_plan |
| Frontend | `frontend/src/**` | every plan's "Frontend Components" section |

---

## Non-negotiables (full list in `../CLAUDE.md`)

- Security first, always. When unsure, choose the safer option.
- Every sensitive action records an audit event.
- Validate all input through marshmallow schemas (`unknown=RAISE`).
- Case-scoped resources return **404** (not 403) to non-members.
- All crypto lives in `core/crypto.py` — never inline.
- No secrets in code; no document content in logs.
