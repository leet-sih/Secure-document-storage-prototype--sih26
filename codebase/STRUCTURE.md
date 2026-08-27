# Project Structure Map

Every file below already exists with a header describing its responsibility (what it does /
returns / stores) and `TODO` markers where implementation goes. Pick a file, read its header,
read the matching `../feature_plans/<feature>_plan.md`, and build.

> **PROTOTYPE STACK:** PostgreSQL is the only service. Chunks + keys live on local disk; there
> is no Redis / MinIO / Vault / Celery / Nginx yet (all deferred — see `infra/README.md` and
> `../docs/ARCHITECTURE.md`). This keeps setup to `docker compose up postgres` + `flask run`.

```
codebase/
├── .env.example              # all env vars (copy to .env)
├── .gitignore
├── README.md                 # setup + ownership split
├── STRUCTURE.md              # this file
├── DEFINITIONS.md            # glossary: every term/library/pattern explained with examples
│
├── backend/                  # Flask 3 API (Python 3.12)
│   ├── requirements.txt
│   ├── Dockerfile            # runs `flask run` (prototype; Gunicorn comes later)
│   ├── wsgi.py               # exports `app` from create_app()
│   ├── seed.py               # idempotent demo data
│   ├── migrations/README.md  # Flask-Migrate flow + hand-written bits (audit REVOKE, FTS trigger)
│   ├── app/
│   │   ├── __init__.py       # create_app() factory  ← wires everything
│   │   ├── config.py         # env-driven config classes
│   │   ├── extensions.py     # db, migrate, jwt, limiter(in-memory), cors singletons
│   │   ├── models/           # ← SHARED CONTRACT (build these first)
│   │   │   ├── department.py user.py case.py case_member.py
│   │   │   ├── document.py document_chunk.py
│   │   │   ├── audit_event.py document_signature.py document_share_link.py
│   │   ├── schemas/          # marshmallow validation/serialization (API contract)
│   │   │   ├── auth_ user_ case_ document_ audit_ signature_ sharing_ search_schemas.py
│   │   ├── core/             # security primitives
│   │   │   ├── crypto.py     # AES-256-GCM + HKDF (ONLY place for raw crypto)  ✅ implemented
│   │   │   ├── kms.py        # master-key store — local file (prototype)
│   │   │   ├── signing.py    # Ed25519 sign/verify
│   │   │   ├── security.py   # bcrypt + JWT access token (no refresh flow in prototype)
│   │   │   ├── rbac.py       # Role enum + @require_roles  ✅ implemented
│   │   │   ├── totp.py       # MFA
│   │   │   ├── rate_limit.py # named limit strings  ✅ implemented
│   │   │   ├── audit_events.py # canonical AuditEventType enum  ✅ implemented
│   │   │   └── errors.py     # JSON error envelope
│   │   ├── services/         # business logic (blueprints stay thin)
│   │   │   ├── audit_service.py     # hash-chain recorder  ✅ record() implemented
│   │   │   ├── auth_ user_ case_ document_ signature_ sharing_ search_service.py
│   │   ├── storage/chunk_store.py   # encrypted chunks on local disk (prototype)
│   │   ├── blueprints/       # HTTP routes (1 per resource)
│   │   │   ├── auth.py users.py cases.py documents.py audit.py
│   │   │   ├── signatures.py sharing.py share_access.py(PUBLIC) search.py
│   │   ├── tasks/maintenance.py     # on-demand cleanup (no Celery in prototype)
│   │   └── tests/            # conftest.py, test_crypto.py, test_audit_chain.py, ...
│
├── frontend/                 # React 18 + Vite (TypeScript)
│   ├── package.json vite.config.ts tsconfig.json tailwind.config.js index.html Dockerfile
│   └── src/
│       ├── main.tsx App.tsx index.css
│       ├── lib/apiClient.ts      # apiFetch (native fetch); attaches token, logs out on 401 (single API source)
│       ├── store/AuthContext.tsx # session (React Context + useReducer); token in localStorage (prototype)
│       ├── hooks/useAuth.ts
│       ├── types/index.ts        # mirrors backend response schemas
│       ├── components/ (README + ProtectedRoute.tsx)
│       └── pages/ (README + LoginPage.tsx)
│
└── infra/
    ├── docker-compose.yml    # PostgreSQL only (backend/frontend run locally)
    └── README.md             # prototype vs. future infrastructure
```

## Suggested build order (unblocks the most people fastest)
1. **Phase 0**: `create_app()`, `config`, `extensions`, `docker compose up postgres`, `flask db upgrade`.
2. **models/** — the shared contract everything imports. Land these + migration first.
3. **core/crypto.py** (done) + **kms.py** + **storage/chunk_store.py** — unblocks documents.
4. **auth + rbac** — unblocks every protected route.
5. Feature verticals in parallel per the ownership table in `README.md`.

Legend: ✅ = already implemented (not just a stub). Everything else is a documented stub with `TODO`.
