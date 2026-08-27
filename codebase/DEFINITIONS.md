# DEFINITIONS — Technical Glossary for the PRAMAAN Codebase

Every technical term, library, and pattern used in this project — explained in plain English
with a concrete example and **where it lives in our code**. If you hit a word you don't know
while reading a file, find it here first.

Legend: 📁 = where it's used in this repo.

**Contents**
1. [Big-picture architecture](#1-big-picture-architecture)
2. [Backend framework & patterns (Flask)](#2-backend-framework--patterns-flask)
3. [Backend libraries](#3-backend-libraries)
4. [Security & cryptography](#4-security--cryptography)
5. [Data layer — database, ORM, storage](#5-data-layer--database-orm-storage)
6. [Async jobs & infrastructure](#6-async-jobs--infrastructure)
7. [Frontend (React)](#7-frontend-react)
8. [Domain model (business terms)](#8-domain-model-business-terms)

---

## 1. Big-picture architecture

### SPA (Single-Page Application)
A website that loads once and then updates the page with JavaScript instead of fetching new
HTML pages from the server. Our frontend is an SPA — the browser downloads the React bundle
once, and navigating between "pages" happens client-side.
📁 `frontend/` (React + Vite build → static files served by Nginx).

### REST API
A style of web API where you act on "resources" (users, cases, documents) using HTTP verbs:
`GET` (read), `POST` (create), `PATCH` (update), `DELETE` (remove). Our backend is a REST API.
Example: `POST /api/v1/cases` creates a case; `GET /api/v1/cases/{id}` reads one.
📁 `backend/app/blueprints/`.

### Endpoint / Route
A single URL + HTTP method the API responds to. Example: `GET /api/v1/audit/verify`.
📁 defined inside blueprint files, e.g. `blueprints/audit.py`.

### Client / Server
The **client** is the browser (React). The **server** is the Flask backend. The client sends
requests; the server processes them and returns JSON (or a file stream).

### Reverse proxy
A server that sits in front of your app servers and forwards requests to them. Ours (Nginx)
receives all HTTPS traffic, forwards `/api/*` to Flask and everything else to the React files,
and adds security headers.
📁 `infra/nginx/nginx.conf`.

### WSGI (Web Server Gateway Interface)
The standard Python interface between a web server and a Python web app. Flask speaks WSGI;
Gunicorn (the production server) runs the WSGI `app` object.
📁 `backend/wsgi.py` exports `app`; `Dockerfile` runs `gunicorn ... wsgi:app`.

### Environment variable (env var)
A configuration value read from the operating system / `.env` file instead of hardcoded in
code. Keeps secrets out of the source. Example: `DATABASE_URL`, `JWT_SECRET`.
📁 declared in `.env.example`, read in `app/config.py`.

### Container / Image (Docker)
An **image** is a packaged, runnable snapshot of software + its dependencies. A **container**
is a running instance of an image. We ship each service (backend, frontend, db…) as a container
so it runs identically on every machine.
📁 `backend/Dockerfile`, `frontend/Dockerfile`, `infra/docker-compose.yml`.

---

## 2. Backend framework & patterns (Flask)

### Flask
A lightweight Python web framework. It maps URLs to Python functions and returns responses.
It's our whole backend. Example:
```python
@auth_bp.route("/login", methods=["POST"])
def login():
    return {"ok": True}
```
📁 all of `backend/app/`.

### Application factory (`create_app()`)
A function that builds and returns the Flask app, instead of creating a global `app` at import
time. This lets tests build a fresh app with test config, and avoids circular imports.
```python
def create_app(config_object=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object or get_config())
    _init_extensions(app)
    _register_blueprints(app)
    return app
```
📁 `backend/app/__init__.py`.

### Blueprint
A group of related routes registered together under a URL prefix. Keeps the app modular — one
blueprint per resource. Example: everything under `/api/v1/auth` lives in the `auth` blueprint.
```python
auth_bp = Blueprint("auth", __name__)
# in create_app: app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
```
📁 `backend/app/blueprints/`.

### Service layer
Plain Python functions that hold the **business logic**, called by the thin blueprint routes.
Keeps routes small (validate → call service → serialize) and logic reusable/testable.
Example: `document_service.upload_document(...)` does the chunk-encrypt-store pipeline; the
route just wires HTTP to it.
📁 `backend/app/services/`.

### Decorator
A function that wraps another function to add behaviour, written with `@`. We use them for auth
and rate limiting. Example — `@require_roles` blocks users without the right role:
```python
@documents_bp.route("/documents/<id>/download")
@jwt_required()
@require_roles(Role.CASE_OFFICER, Role.INVESTIGATOR, Role.SUPER_ADMIN)
def download(id, current_user): ...
```
📁 `core/rbac.py` (`require_roles`), `core/rate_limit.py`.

### Singleton (extension instances)
One shared instance of an object used across the app. We create `db`, `jwt`, `limiter` etc.
once (without an app) and bind them to the app inside `create_app()`. Avoids circular imports.
```python
db = SQLAlchemy()          # created once in extensions.py
# ... later:  db.init_app(app)
```
📁 `backend/app/extensions.py`.

### Middleware
Code that runs on every request before/after the route handler (e.g. auth checks, CORS, rate
limiting). In Flask this is done via extensions and `before_request` hooks.
📁 `jwt`, `limiter`, `cors` in `extensions.py`.

---

## 3. Backend libraries

### Flask-SQLAlchemy / SQLAlchemy (ORM)
**ORM = Object-Relational Mapper.** Lets you work with database rows as Python objects instead
of writing raw SQL. A **model** class maps to a table; an instance maps to a row.
```python
class User(db.Model):
    email = db.Column(db.Text, unique=True)
User.query.filter_by(email="a@b.com").first()   # SELECT ... WHERE email=...
```
📁 `backend/app/models/`, `db` from `extensions.py`.

### Flask-Migrate (Alembic)
Manages **database migrations** — versioned scripts that change the DB schema over time so
everyone's database stays in sync. Example: after adding a column to a model you run
`flask db migrate -m "add phone"` then `flask db upgrade`.
📁 `backend/migrations/`.

### marshmallow (Schema)
Validates incoming request JSON and serializes outgoing responses. A **schema** declares the
expected fields, types, and rules. It's our guard against bad/malicious input.
```python
class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=1, max=128))
data = LoginSchema().load(request.json)   # raises 400 if invalid
```
📁 `backend/app/schemas/`.

### Flask-JWT-Extended
Issues and verifies **JWT** access tokens (see §4). Provides `@jwt_required()` and
`get_jwt_identity()`.
📁 `core/security.py`, `core/rbac.py`, `extensions.py` (`jwt`).

### Flask-Limiter
**Rate limiting** — caps how many requests an IP/user can make in a time window, to stop brute
force and scraping. **Prototype:** backed by in-memory storage (`memory://`). Production:
Redis-backed for cross-worker accuracy.
```python
@auth_bp.route("/login")
@limiter.limit("5 per minute")
def login(): ...
```
📁 `core/rate_limit.py` (named limits), `extensions.py` (`limiter`).

### bcrypt
A deliberately **slow password-hashing** algorithm. Slow = hard to brute-force. We store the
bcrypt hash of a password, never the password itself. ⚠️ Only uses the first **72 bytes**.
```python
hash = bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=12))
bcrypt.checkpw(pw.encode(), hash)   # True/False
```
📁 `core/security.py`.

### pyotp
Generates and verifies **TOTP** codes (the 6-digit MFA codes from Google Authenticator).
```python
import pyotp
pyotp.TOTP(secret).verify("123456", valid_window=1)   # ±30s drift
```
📁 `core/totp.py`.

### cryptography
The library that does our real encryption: **AES-256-GCM**, **HKDF** key derivation, and
**Ed25519** signatures (see §4). All raw crypto is confined to two files.
📁 `core/crypto.py` (AES/HKDF), `core/signing.py` (Ed25519).

### chunk_store (local, prototype)
Provides `put_chunk`, `get_chunk`, and `delete_document` over **local disk**. Encrypted chunks
land in `./data/chunks/{doc_id}/chunk_000000`. In production this swaps to MinIO (same API,
different backend — that's the whole point of the interface).
📁 `storage/chunk_store.py`.

### minio (client) — deferred to production
Python client for **MinIO** object storage. Not used in the prototype — the local chunk store
replaces it. MinIO returns when we move to production (see `infra/README.md`).

### redis (client) — deferred to production
Python client for **Redis**. Not used in the prototype. Redis comes back when we add refresh
tokens, Redis-backed rate limiting, and the TOTP replay guard in production.

### celery — deferred to production
Runs **background jobs** outside the request/response cycle. Not used in the prototype; cleanup
is a plain function instead. Celery + beat return in production for scheduled cleanup, OCR, and
embedding jobs.
📁 `tasks/maintenance.py` (`sweep_orphaned_documents()` — called on demand, not scheduled).

### hvac — deferred to production
Python client for **HashiCorp Vault**. Not used in the prototype — the local file KMS replaces
it. Vault returns in production via `core/kms.py`.
📁 `core/kms.py`.

### python-magic
Detects a file's real type by reading its **magic bytes** (the signature at the start of the
file) instead of trusting the filename or the browser-supplied Content-Type. Stops someone
uploading `virus.exe` renamed to `report.pdf`.
```python
magic.from_buffer(file.read(2048), mime=True)   # -> "application/pdf"
```
📁 used in the upload path, `services/document_service.py`.

### Flask-CORS
Controls **CORS** (Cross-Origin Resource Sharing) — which website origins are allowed to call
our API from a browser. We allow only our own frontend origin, with credentials (cookies).
📁 `extensions.py` (`cors`), configured from `CORS_ORIGINS`.

### structlog
**Structured logging** — logs as key/value data instead of plain strings, easier to search.
Rule: never log document content, passwords, keys, or PII — only IDs and event types.
📁 wired in `app/__init__.py` `_configure_logging`.

### gunicorn — deferred to production
The production **WSGI server** that runs Flask under load with multiple worker processes. Not
used in the prototype — the Dockerfile runs `flask run` instead. Gunicorn comes back when we
switch to production.
📁 `backend/Dockerfile` (`flask run` now; Gunicorn later).

### psycopg
The **PostgreSQL driver** — the low-level library SQLAlchemy uses to talk to Postgres. We use
the synchronous `psycopg` (v3), NOT `asyncpg`, because Flask is synchronous.
📁 `DATABASE_URL=postgresql+psycopg://...` in `.env`.

### pytest / pytest-flask
The **testing** framework. `pytest-flask` adds fixtures (like a test `client`) for Flask apps.
📁 `backend/tests/`.

### ruff / black
**ruff** = fast linter (catches mistakes/bad style). **black** = auto-formatter (consistent
formatting). Run both before pushing.

---

## 4. Security & cryptography

### Encryption at rest / in transit
**At rest** = data is encrypted while stored (our chunks in MinIO). **In transit** = data is
encrypted while moving over the network (TLS/HTTPS). We do both.

### AES-256-GCM
Our symmetric encryption. **AES** = the cipher; **256** = key size in bits; **GCM** = a mode
that also produces an **authentication tag** proving the ciphertext wasn't tampered with.
Same key both encrypts and decrypts. Each document chunk is encrypted with AES-256-GCM.
📁 `core/crypto.py` (`encrypt_chunk`, `decrypt_chunk`).

### Symmetric vs asymmetric
**Symmetric** = one secret key for both encrypt and decrypt (AES). **Asymmetric** = a key
*pair*: a private key and a public key (Ed25519 signatures, TLS). We use both.

### IV / Nonce
"Initialization Vector" / "number used once" — a random value fed into encryption so that
encrypting the same data twice gives different ciphertext. Must be unique per key. We use a
random 12-byte IV per chunk. Safe because each chunk also has its own key.
📁 `core/crypto.py` (`iv = os.urandom(12)`), stored as `DocumentChunk.iv_hex`.

### Auth tag (GCM tag)
A 16-byte value AES-GCM appends to the ciphertext. On decrypt, if the ciphertext or tag was
changed, decryption fails (`InvalidTag`). This is how we detect tampering. We do **not** store
it separately — the `cryptography` library keeps it inside the ciphertext blob in MinIO.
📁 `core/crypto.py`; explained in `models/document_chunk.py`.

### HKDF (key derivation)
"HMAC-based Key Derivation Function" — turns one master key into many independent sub-keys. We
derive a **unique key per chunk** from the document's master key + the chunk index. Because
each key encrypts exactly one chunk, IV reuse (a catastrophic GCM failure) is impossible.
```python
chunk_key = HKDF(master_key, salt=doc_id, info=f"chunk-{i}")
```
📁 `core/crypto.py` (`derive_chunk_key`).

### Chunked encrypted storage (our core innovation)
Instead of encrypting a document as one blob, we split it into 1 MB **chunks**, encrypt each
with its own derived key, and store them under **opaque random keys** (no structure in the
filename). The master key lives in the KMS. The chunk ordering lives only in the DB.
A thief needs the DB **and** chunk store **and** KMS — and the DB alone reveals nothing about
document structure from the chunk store.
**Prototype:** chunk store = `./data/chunks/` on Server B (local or sftp); KMS = `./data/keys/`.
**Production:** chunk store = MinIO; KMS = HashiCorp Vault.
📁 `services/document_service.py`, `feature_plans/chunked_document_storage_plan.md`.

### Integrity hash
A **SHA-256** hash computed over all chunk hashes in order, stored on the document. On download
we recompute it; a mismatch means tampering → we refuse to serve the file (HTTP 422).
📁 `core/crypto.py` (`compute_integrity_hash`), `Document.integrity_hash`.

### SHA-256 (hash)
A one-way function turning any data into a fixed 64-hex-char fingerprint. Same input → same
hash; you can't reverse it. Used for integrity checks, the audit chain, and hashing share
tokens. (Never used for passwords — that's bcrypt's job.)
📁 `core/crypto.py`, `services/audit_service.py`.

### Ed25519 (digital signature)
A fast, modern **asymmetric** signature scheme. A user signs a document's integrity hash with
their **private key**; anyone can verify it with their **public key**. Proves *who* approved a
document and that it hasn't changed since.
📁 `core/signing.py`, `models/document_signature.py`.

### Hash chain (tamper-evident audit log)
Each audit event stores the hash of the previous event (`prev_hash`) plus its own hash
(`this_hash`). Changing any past event breaks every hash after it. `GET /audit/verify`
recomputes the chain and returns `first_break_at` — the ID of the first failing event.
**Tamper-evident** means modification is *detectable*, not impossible.
📁 `services/audit_service.py`, `models/audit_event.py`.

### JWT (JSON Web Token)
A signed token the client sends on every request to prove who they are. It's **stateless** —
the server verifies the signature instead of looking it up. **Prototype:** 8h access token, no
refresh flow. **Production:** 15-min access + 7-day refresh. Format: `header.payload.signature`.
📁 `core/security.py` (`issue_access_token`), verified by `@jwt_required()`.

### Access token vs refresh token
**Access token** = JWT sent on every API call. **Prototype:** 8h TTL, stored in localStorage.
**Production:** 15-min TTL (short damage window if stolen) + a long-lived **refresh token**
(7 days, httpOnly cookie) to silently renew it without re-login.
📁 `core/security.py`, full production flow in `feature_plans/auth_plan.md`.

### httpOnly cookie — production feature
A cookie that JavaScript **cannot** read. We plan to store the production refresh token this way
(XSS-safe). **Prototype skips this** — only a single 8h access token, stored in localStorage.
📁 planned in `blueprints/auth.py` (production); `store/authStore.ts` (prototype uses localStorage).

### Token rotation — production feature
Each time a refresh token is used, it's deleted and a new one issued — so a stolen token is
single-use. **Not implemented in prototype** (no refresh tokens).
📁 planned in `core/security.py`.

### MFA / TOTP (Multi-Factor Authentication)
Requires a second proof beyond the password — a 6-digit **TOTP** code from an authenticator
app that changes every 30 seconds. Even a stolen password isn't enough to log in.
**Step-up MFA:** for sensitive actions (sign, share, delete, manage users), a fresh TOTP
re-check is required if the session's last MFA verification is older than 15 minutes.
📁 `core/totp.py`, `core/rbac.py` (`@require_recent_mfa`), `feature_plans/auth_plan.md`.

### RBAC (Role-Based Access Control)
Permissions are tied to **roles**, not individuals. Our roles: SUPER_ADMIN, CASE_OFFICER,
INVESTIGATOR, PROSECUTOR, AUDITOR, VIEWER. `@require_roles(...)` guards each route.
📁 `core/rbac.py`.

### Case-scoped access (404 not 403)
A user can only see cases they're a member of. For a case they can't see, we return **404 Not
Found**, not 403 Forbidden — so the API never even confirms that a hidden case exists.
📁 `services/case_service.py` (`get_case_for_user`).

### KMS (Key Management System)
The secure store for encryption keys. We abstract it so the app doesn't care which backend:
`EnvKMS` (a persistent file stub for the prototype) or `VaultKMS` (HashiCorp Vault in prod).
Master keys live here, never in the database.
📁 `core/kms.py`.

### TLS / HTTPS / self-signed cert
**TLS** encrypts traffic between browser and server; **HTTPS** is HTTP over TLS. For the demo
we use a **self-signed certificate** (not from a trusted authority), so browsers show a warning
you click past.
📁 `infra/nginx/nginx.conf`, `infra/nginx/certs/README.md`.

### Security headers (HSTS, CSP, etc.)
Extra HTTP response headers that harden the browser: **HSTS** forces HTTPS, **CSP**
(Content-Security-Policy) blocks unauthorized scripts (anti-XSS), **X-Frame-Options** blocks
clickjacking.
📁 `infra/nginx/nginx.conf`.

### XSS / CSRF / SQL injection (attacks we defend against)
**XSS** = injecting malicious JS into a page (mitigated by CSP + not storing tokens in JS-readable
places). **CSRF** = tricking a logged-in user's browser into making a request (mitigated by
SameSite cookies). **SQL injection** = sneaking SQL through input (mitigated by the ORM's
parameterized queries — never string-concatenating SQL).

---

## 5. Data layer — database, ORM, storage

### PostgreSQL
Our relational **database** — stores structured data in tables with rows/columns: users, cases,
document metadata, chunk references, audit log. Note: it stores document **metadata**, never the
file contents.
📁 runs as the `postgres` container; accessed via SQLAlchemy.

### Table / Row / Column / Primary key / Foreign key
A **table** is like a spreadsheet; a **row** is one record; a **column** is a field. A
**primary key** uniquely identifies a row (usually `id`). A **foreign key** links a row to
another table (e.g. `document.case_id` → `cases.id`).
📁 `backend/app/models/`.

### Model
A Python class mapping to a database table (the ORM concept). Each attribute is a column.
```python
class Case(db.Model):
    __tablename__ = "cases"
    id = db.Column(UUID(as_uuid=True), primary_key=True)
    case_number = db.Column(db.Text, unique=True)
```
📁 `models/case.py`.

### Migration
A versioned script that changes the DB schema (add table/column/index). Generated by
Flask-Migrate. Applied with `flask db upgrade`. Everyone runs the same migrations to keep DBs
identical.
📁 `migrations/`.

### UUID
"Universally Unique Identifier" — a random 128-bit id like
`a1b2c3d4-1234-5678-abcd-ef1234567890`. We use UUIDs for public ids (users, cases, documents)
so they can't be guessed/enumerated like `1, 2, 3`.
📁 all models' `id` columns.

### Soft delete
Marking a row as deleted (`is_deleted = True`) instead of actually removing it — so the audit
trail and chunks survive for legal reasons. The UI hides soft-deleted documents.
📁 `models/document.py` (`is_deleted`), `services/document_service.py` (`soft_delete`).

### Index / GIN index
A database structure that makes lookups fast. A **GIN index** specifically speeds up full-text
search (`tsvector`) and array columns.
📁 documents' `search_vector` GIN index (see `migrations/README.md`).

### tsvector / Full-Text Search (FTS)
PostgreSQL's built-in text search. A `tsvector` column holds pre-processed searchable text; a
query matches against it. Powers metadata search without an external search engine.
📁 `models/document.py` (`search_vector`), `services/search_service.py`.

### Local chunk store (prototype — Server B)
The prototype's object storage. Encrypted chunks land on the filesystem at
`./data/chunks/{opaque_storage_key}` — flat namespace, no doc IDs or chunk indexes in filenames.
The chunk store lives on a separate host (Server B) in the demo. The interface
(`put_chunk`, `get_chunk`, `delete_chunks`) is the swap point for MinIO in production.
📁 `storage/chunk_store.py`.

### MinIO / Object storage — production target
An S3-compatible **object store** for arbitrary files. We'll store each encrypted chunk as an
object at key `doc-chunks/{doc_id}/chunk_000001`. Deferred to production; prototype uses local
disk via `chunk_store.py` instead.

### Bucket / Object key
A **bucket** is a top-level container in object storage (ours: `doc-chunks`, private). An
**object key** is the path to one object inside it. Same concept applies to our local path
`{doc_id}/chunk_000001` in the prototype.

### HashiCorp Vault — production target
A dedicated secrets manager that stores document **master keys** and signing private keys.
Deferred to production. **Prototype:** local file KMS (`core/kms.py`) stores AES-wrapped master
keys at `./data/keys/{doc_id}.key` — same interface, simpler backend.
📁 `core/kms.py` (both prototype and production share this interface).

---

## 6. Async jobs & infrastructure

### Redis — deferred to production
An in-memory data store, extremely fast. **Production** uses it for: refresh-token storage,
rate-limit counters, the TOTP replay guard, and as Celery's message broker. **Prototype:** not
running — rate limiting is in-memory (Flask-Limiter `memory://`), no refresh tokens, TOTP
replay guard is skipped (valid_window=1 is the sole protection).

### TTL (Time To Live)
An expiry on a stored value — after N seconds it auto-deletes. Example: a refresh token key
lives 7 days; a used-TOTP marker lives 60 seconds.
📁 Redis keys in `core/security.py`, `core/totp.py`.

### Celery / Task / Worker / Broker / Beat — deferred to production
**Celery** runs background **tasks** so slow work doesn't block API responses. A **worker** is a
process that executes tasks. The **broker** (Redis) is the queue. **Beat** fires periodic tasks.
**Prototype:** Celery is not running. Cleanup is a plain on-demand function instead.
```python
# prototype (no Celery):
from app.tasks.maintenance import sweep_orphaned_documents
sweep_orphaned_documents()   # call this manually when needed
```
📁 `tasks/maintenance.py` (prototype); Celery + beat return in production.

### Idempotent
An operation you can run repeatedly with the same result — no duplicates or damage. Our seed
script and startup migrations are idempotent so re-running them is safe.
📁 `backend/seed.py`.

### Docker Compose
A tool to define and run a multi-container app from one YAML file. **Prototype:**
`docker compose up postgres` starts only PostgreSQL — backend and frontend run locally with
`flask run` and `npm run dev`. **Production:** full stack (Redis, MinIO, Vault, Celery, Nginx)
all in compose.
📁 `infra/docker-compose.yml`.

### Healthcheck / depends_on
A **healthcheck** tells Docker when a container is actually ready (not just started).
`depends_on: condition: service_healthy` makes the backend wait for the DB to be ready before
starting — avoids crash-on-boot.
📁 `infra/docker-compose.yml`.

### Nginx
A fast web server we use as the **reverse proxy**: terminates HTTPS, forwards `/api/*` to Flask
and everything else to the React static files, applies rate limits and security headers.
📁 `infra/nginx/nginx.conf`.

### Streaming (upload/download)
Processing a file piece-by-piece instead of loading it all into memory. We stream uploads
through the chunker (`request.stream`) so a 500 MB file never sits fully in RAM.
📁 `services/document_service.py`, `blueprints/documents.py`.

---

## 7. Frontend (React)

### React
A JavaScript library for building UIs from reusable **components**. The UI is a function of
state — when state changes, React re-renders.
📁 `frontend/src/`.

### Component
A reusable, self-contained piece of UI (a function returning JSX). Example: `<ProtectedRoute>`,
`<LoginPage>`, `<CaseCard>`.
📁 `frontend/src/components/`, `frontend/src/pages/`.

### JSX / TSX
HTML-like syntax inside JavaScript/TypeScript. `.tsx` = a TypeScript file containing JSX.
```tsx
return <button onClick={submit}>Log in</button>;
```

### Vite
The frontend **build tool + dev server**. Gives instant hot-reload in dev and bundles the app
for production. Faster alternative to older tools like webpack.
📁 `frontend/vite.config.ts`.

### TypeScript
JavaScript **with types**. Catches errors before running (e.g. passing a string where a number
is expected). Our `types/index.ts` mirrors the backend's JSON shapes.
📁 `frontend/src/types/index.ts`, `tsconfig.json`.

### React Router
Handles client-side **routing** — showing different components for different URLs without a
full page reload. Example: `/login` → `<LoginPage>`, `/cases/:id` → `<CaseDetailPage>`.
📁 `frontend/src/App.tsx`.

### Hook / Custom hook
A React function starting with `use` that adds behaviour/state to a component. Built-in:
`useState`, `useEffect`. Ours: `useAuth()` bundles login/logout/session logic.
📁 `frontend/src/hooks/useAuth.ts`.

### AuthContext / useAuth (session management)
React Context + `useReducer` holding `{ user, status }`. The access token is stored in
`localStorage` (dms_access_token) for prototype convenience and read by `apiFetch()` directly —
so the HTTP layer works outside the component tree. **Production:** in-memory token + httpOnly
refresh cookie (no localStorage). Replaced Zustand (removed in CHANGES.md §5).
```tsx
const { user, setSession, clear } = useAuth();  // inside <AuthProvider>
```
📁 `frontend/src/store/AuthContext.tsx`.

### apiFetch / native fetch (HTTP client)
The single async function all API calls go through. Reads the access token from `localStorage`,
attaches `Authorization: Bearer`, checks `res.ok` (fetch does NOT reject on 4xx/5xx — this
check replaces what Axios did automatically), and handles 401 by clearing the token and
redirecting to `/login`. On `401 { code: "MFA_REQUIRED" }`, shows the step-up TOTP modal
instead of redirecting. Replaced Axios (removed in CHANGES.md §5).
📁 `frontend/src/lib/apiClient.ts`.

### Tailwind CSS
A styling approach using small utility classes directly in markup, e.g.
`className="flex gap-2 rounded bg-blue-600 p-2"`. Fast, consistent styling with no separate CSS
files per component.
📁 `frontend/tailwind.config.js`, `frontend/src/index.css`.

### Protected route
A wrapper component that blocks a page unless the user is authenticated (and, optionally, has
the right role) — redirecting to `/login`, `/change-password`, or `/mfa-setup` as needed.
📁 `frontend/src/components/ProtectedRoute.tsx`.

---

## 8. Domain model (business terms)

These are the real-world concepts the system manages. Each maps to a database table/model.

### Department
An organizational unit — a police station, court, forensic lab, or legal department. Users and
cases belong to one.
📁 `models/department.py`.

### User & Roles
An account. Every user has one system **role** that governs what they can do:
| Role | Can do |
|------|--------|
| SUPER_ADMIN | manage users, see all cases + audit logs |
| CASE_OFFICER | create/manage cases, upload documents |
| INVESTIGATOR | view + sign documents in assigned cases |
| PROSECUTOR | read case files shared with them |
| AUDITOR | read audit logs only |
| VIEWER | read one document via a time-limited link |
📁 `models/user.py`, `core/rbac.py`.

### Case
The top-level container for an investigation/proceeding. **Everything** (documents, audit
events, members) hangs off a case. Has a lifecycle: OPEN → UNDER_INVESTIGATION → CLOSED →
ARCHIVED.
📁 `models/case.py`.

### Case member
The link between a user and a case, with a per-case role. Drives access control — you see a
case only if you're an active member.
📁 `models/case_member.py`.

### Document
A file's **metadata** record (name, type, size, chunk count, integrity hash). The actual bytes
live as encrypted chunks in the chunk store (local disk in prototype, MinIO in production) —
never in this row. Types include FIR, CHARGE_SHEET, FORENSIC_REPORT, WITNESS_STATEMENT, etc.
📁 `models/document.py`.

### Document chunk
One encrypted 1 MB piece of a document. Stores its `storage_key` (local file path in prototype /
MinIO object key in production), IV, and ciphertext hash — enough to fetch, verify, and decrypt
it, but not the master key itself.
📁 `models/document_chunk.py`.

### Audit event
An immutable record of one action (login, upload, download, role change…), hash-chained to the
previous event for tamper-evidence. This is the compliance backbone.
📁 `models/audit_event.py`, `services/audit_service.py`.

### Document signature
An Ed25519 signature by a user over a document's integrity hash — legal proof of who approved
it and that it's unchanged since.
📁 `models/document_signature.py`.

### Share link
A time-limited, single-purpose token that lets an external party (e.g. a prosecutor without an
account) download one document. We store only the **hash** of the token; the raw token is shown
to the creator once.
📁 `models/document_share_link.py`, `blueprints/share_access.py` (the public endpoint).

### FIR (First Information Report)
The document the police file when they first record a cognizable offence — a common document
type in this system (`doc_type = "FIR"`). Other domain doc types: charge sheet, witness
statement, forensic report, court filing, judgment, legal notice, evidence record.

---

*Keep this file updated: when you introduce a new library or concept, add a short entry here so
the next teammate isn't blocked.*
