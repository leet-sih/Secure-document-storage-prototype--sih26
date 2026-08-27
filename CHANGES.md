# CHANGES.md — what the submitted PPT now commits us to

**Purpose:** the idea-submission deck (`ppts/SIH2026_PS26190_leet_Idea_Submission_v1.pptx`) makes
specific claims about the prototype. Some of them do not match what is currently written in
`docs/`, `feature_plans/` and `codebase/`. This file lists every gap, in the order it is worth
fixing, so the deck and the code stay the same story.

**How to use:** each item has *Claim* (what the deck says), *Now* (what the repo says today),
*Do* (the change), *Files*, and *Done when*. Work top-down — P0 items are things a judge can
catch in five minutes.

**Status legend:** `[P0]` deck says it, code contradicts it · `[P1]` deck says it, code is silent
· `[P2]` wording / documentation only

---

## 0. Baseline → now, in one table

| Area | Where we started | What the deck now says |
|---|---|---|
| Product name | "Secure DMS" | **PRAMAAN — Secure Evidence Vault** |
| Deployment | One host, `./data/chunks` + `./data/keys` side by side | **Two servers**: Server A (PostgreSQL/metadata), Server B (encrypted chunk store); KMS boundary undecided |
| Frontend state/HTTP | Zustand + Axios | **React Context + `fetch`** |
| OCR | Roadmap R1, explicitly "do NOT implement" | **In prototype scope**, Day 6 |
| Upload cap | `MAX_FILE_SIZE_MB=100` | **500 MB** |
| Sharing | 48h link, `allowed_email` optional | **Recipient-bound** — a named recipient, not an open link |
| MFA | TOTP at login only | TOTP at login **+ re-check before sensitive actions** |
| Audit claim | "blockchain-lite", "immutable" | **Tamper-evident** hash chain — detection, not immutability |
| Architecture adjective | "zero-trust" | **least-privilege** |
| Legal framing | IT Act / BSA / CERT-In cited | **All legal claims removed** |
| Related national systems | — | **Not mentioned at all**; PRAMAAN is standalone |

---

## 1. `[P0]` Split the chunk store onto a second host

**Claim (slide 2 + 3):** Server A holds metadata, Server B holds ciphertext, and *"compromising
either storage server on its own does not yield enough information to reconstruct a document."*

**Now:** `.env.example` puts `CHUNK_STORAGE_DIR=./data/chunks` and `KMS_DIR=./data/keys` on the
same machine as the app and the database. That is logical separation only — a judge will call it.

**Do:**

1. Add host-aware config. In `codebase/.env.example`:

```bash
# ── Storage topology (prototype: two hosts) ──
# SERVER A = PostgreSQL (metadata). SERVER B = encrypted chunk store (ciphertext only).
CHUNK_STORE_BACKEND=local          # local | sftp | http
CHUNK_STORE_HOST=                  # blank = same host (dev only); set for the two-server demo
CHUNK_STORAGE_DIR=./data/chunks    # path ON Server B
CHUNK_STORE_USER=
CHUNK_STORE_KEYFILE=               # SSH key for the sftp backend

# KMS boundary is NOT yet decided — see CHANGES.md §2
KMS_DIR=./data/keys
```

2. In `codebase/backend/app/config.py`, add the matching `CHUNK_STORE_BACKEND`,
   `CHUNK_STORE_HOST`, `CHUNK_STORE_USER`, `CHUNK_STORE_KEYFILE` entries next to the existing
   `CHUNK_STORAGE_DIR`.

3. In `codebase/backend/app/storage/chunk_store.py`, keep the four public functions exactly as
   they are (`chunk_path`, `put_chunk`, `get_chunk`, `delete_document`) and dispatch internally on
   `CHUNK_STORE_BACKEND`. The whole point of that module is that `document_service` never changes.

```python
# storage/chunk_store.py
def _backend():
    return current_app.config["CHUNK_STORE_BACKEND"]

def put_chunk(document_id: str, index: int, data: bytes) -> str:
    if _backend() == "local":
        return _put_local(document_id, index, data)
    if _backend() == "sftp":
        return _put_sftp(document_id, index, data)   # paramiko, key auth, no password
    raise ValueError(f"unknown chunk store backend: {_backend()}")
```

4. Server B gets its **own OS user and its own credentials**. The app account must be able to
   write chunk objects and nothing else. Do not reuse the database credentials.

**Files:** `codebase/.env.example`, `backend/app/config.py`, `backend/app/storage/chunk_store.py`,
`backend/requirements.txt` (add `paramiko` if you take the sftp route), `SETUP.md`,
`docs/ARCHITECTURE.md`.

**Done when:** the demo runs with Postgres on one machine and the chunk directory on another, and
you can show that the chunk-store host has no database access and no key material on it.

---

## 2. `[P0]` Decide and document the KMS boundary

**Claim (slide 2 + 3):** the KMS is drawn as a third trust domain, labelled *"boundary being
finalised"*. Slide 4 lists KMS/master-key compromise under **partially addressed**.

**Now:** `core/kms.py` writes AES-wrapped keys to `KMS_DIR` on the app host, wrapped with
`SECRET_KEY` — which is also the Flask signing key.

**Do:**

1. Pick one and write it down in `docs/ARCHITECTURE.md`:
   - **(a)** third host — strongest, matches the diagram best;
   - **(b)** app host, separate OS user + separate wrapping key — honest middle ground;
   - **(c)** with Server A — weakest, say so out loud if you choose it.
2. Whichever you pick: **stop reusing `SECRET_KEY` to wrap master keys.** Add a dedicated
   `KMS_WRAPPING_KEY` env var. Two different jobs should never share one secret.
3. Add a **Key lifecycle** section to `docs/SECURITY.md` covering generation, storage, access,
   rotation, backup, recovery, revocation, destruction and compromise response. Mark each line
   *implemented* or *required hardening* — do not let it read as though it already exists.

**Files:** `backend/app/core/kms.py`, `backend/app/config.py`, `.env.example`,
`docs/SECURITY.md`, `docs/ARCHITECTURE.md`.

**Done when:** someone can ask "where do the keys live and who can read them?" and get one
sentence back, and `grep -r SECRET_KEY` shows it is no longer wrapping master keys.

---

## 3. `[P0]` Upload cap: 100 MB → 500 MB

**Claim (slide 3):** *"up to 500 MB (prototype limit)"*, twice.

**Now:** `MAX_FILE_SIZE_MB=100` in `.env.example`, and `Config.MAX_CONTENT_LENGTH` derives from it.

**DECISION REQUIRED — pick one:**
- **Align code to deck:** set `MAX_FILE_SIZE_MB=500`. Then actually test a 500 MB upload, because
  §12's benchmark table promises figures at that size and the pre-verify pass buffers the whole
  document in RAM (see `feature_plans/chunked_document_storage_plan.md`, "Important design note").
- **Align deck to code:** I change the two slide-3 captions to 100 MB. Cheaper and safer if you
  are not confident a 500 MB round-trip will hold on demo hardware.

**Files:** `codebase/.env.example`, `backend/app/config.py`, `docs/EDGE_CASES.md` §5.1
(currently says 500 MB — already inconsistent with `.env`).

**Done when:** `.env.example`, `config.py`, `EDGE_CASES.md` and the deck all say the same number.

---

## 4. `[P0]` Opaque chunk storage keys

**Claim:** Server B is *"ciphertext only … no keys, no plaintext"* and its ordering lives in the
metadata on Server A.

**Now:** `document_chunk.py` documents `storage_key` as `{doc_id}/chunk_{index:06d}`. Anyone with
the chunk directory can read document boundaries and chunk order straight off the filenames — so
Server B leaks structure even though it leaks no content.

**Do:** generate an opaque object id per chunk and keep the ordering only in the database.

```python
# in the upload path, per chunk
storage_key = secrets.token_hex(16)         # e.g. "a8f13c...", flat namespace
chunk_store.put_chunk(storage_key, ciphertext)
```

- `DocumentChunk.storage_key` stays `TEXT` — no migration needed, only the value changes.
- `chunk_store.delete_document()` can no longer glob a folder: delete by the key list from the DB.
- Update the docstrings in `storage/chunk_store.py` and `models/document_chunk.py`.

**Files:** `backend/app/storage/chunk_store.py`, `backend/app/services/document_service.py`,
`backend/app/models/document_chunk.py`, `feature_plans/chunked_document_storage_plan.md`.

**Done when:** `ls` on the chunk store shows a flat list of opaque names, and deleting a document
still removes exactly its own chunks.

---

## 5. `[P0]` Drop Zustand and Axios

**Claim (slide 3 tech strip):** frontend is React + Flask; no state-management or HTTP library is
named. Earlier decks listed Zustand and Axios; those are gone.

**Now:** `frontend/package.json` still depends on both, and they are imported in `authStore.ts`
and `apiClient.ts`.

**Do:** the cost is two files — every consumer (`useAuth.ts`, `ProtectedRoute.tsx`, `App.tsx`,
`LoginPage.tsx`) is still a `TODO` stub, so nothing else breaks.

1. Replace `src/store/authStore.ts` with `src/store/AuthContext.tsx` — `createContext` +
   `useReducer` holding `{ user, status }`.
2. **Stop keeping the token in React state.** It is already mirrored to `localStorage` on every
   `setSession()` / `clear()`, so `apiFetch` can read it directly — which is what lets the HTTP
   layer work outside a component tree, the one thing Zustand was buying us.

```ts
// src/lib/apiClient.ts
const TOKEN_KEY = "dms_access_token";

export async function apiFetch(path: string, init: RequestInit = {}) {
  const token = localStorage.getItem(TOKEN_KEY);
  const res = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (res.status === 401) {
    localStorage.removeItem(TOKEN_KEY);
    if (location.pathname !== "/login") location.assign("/login");
    throw new Error("unauthorised");
  }
  if (!res.ok) throw new Error((await res.json())?.error?.message ?? res.statusText);
  return res.status === 204 ? null : res.json();
}
```

> `fetch` only rejects on network failure, never on 4xx/5xx. The explicit `res.ok` check above is
> the behaviour Axios gave us for free — do not drop it.

3. `npm uninstall zustand axios`, then remove both lines from `package.json` dependencies.

**Files:** `frontend/package.json`, `frontend/src/store/authStore.ts` → `AuthContext.tsx`,
`frontend/src/lib/apiClient.ts`, `frontend/src/hooks/useAuth.ts`,
`frontend/src/components/ProtectedRoute.tsx`, `codebase/DEFINITIONS.md` (§7 entries for Zustand
and Axios).

**Done when:** `grep -r "zustand\|axios" frontend/src` returns nothing and the login flow works.

---

## 6. `[P0]` OCR moves from roadmap into the prototype

**Claim (slide 2 feature card + slide 3 tech strip + slide 4 Day 6):** *"Scanned FIRs and charge
sheets become searchable text, entirely on-premise. Devanagari, Tamil, Telugu, Bengali and
Gujarati; low-confidence pages flagged for review."*

**Now:** `feature_plans/ocr_plan.md` opens with **"Do NOT implement for the Sep 2 prototype"**, and
the plan's pipeline is built on a Celery task — but the prototype has no Celery and no Redis.

**Do:**

1. Flip the status banner at the top of `feature_plans/ocr_plan.md` from roadmap to prototype
   scope, and rewrite the execution model — **no Celery**. Options, easiest first:
   - run OCR inline on upload for small scans, with a hard page cap;
   - run it in a `threading.Thread` after the upload response is returned;
   - add a `flask ocr-pending` CLI command the demo operator runs.
   Pick one and write it in the plan. Inline is simplest and demos fine at one or two pages.
2. The DB columns already exist — `Document.ocr_status`, `ocr_confidence`, `search_text`,
   `search_vector`. Add `ocr_language` and `ocr_page_count` if you want the plan's full shape.
3. Build `backend/app/core/ocr.py`: `preprocess_image()`, `run_tesseract()`, `score_confidence()`.
4. Confidence gating is a **deck promise** — implement the three-way outcome: `DONE` (≥80),
   `LOW_CONFIDENCE` (60–79, searchable but flagged), `FAILED` (<60, not searchable).
5. Add to `requirements.txt`: `pytesseract`, `Pillow`, `pdf2image`, `PyMuPDF`,
   `opencv-python-headless`, `numpy`. Add to `backend/Dockerfile`: `tesseract-ocr`,
   `tesseract-ocr-hin`, `tesseract-ocr-tam`, `tesseract-ocr-tel`, `tesseract-ocr-ben`,
   `tesseract-ocr-guj`, `poppler-utils`.
   **Note the deck names five Indic scripts — install all five or change the slide.**
6. Security line to hold: OCR reconstructs the document in memory on the app server, writes only
   derived text to `search_text`, and never persists a decrypted file. Say this in the code
   comment too, because it is the question a judge will ask.

**Files:** `feature_plans/ocr_plan.md`, `backend/app/core/ocr.py` (new),
`backend/app/services/document_service.py`, `backend/app/models/document.py`,
`backend/requirements.txt`, `backend/Dockerfile`, `docs/TODO.md`.

**Done when:** a scanned PDF uploads, `ocr_status` lands on one of the three values, and the
extracted text is findable through `/documents/search`.

---

## 7. `[P0]` Search must cover OCR text

**Claim (slide 2):** search spans *"filenames, tags, document type, dates and digitised text, in
one query"* and *"results are always filtered to what that officer is allowed to see."*

**Now:** `search_plan.md` populates `search_text` only for plaintext formats; the FTS trigger
exists but nothing writes OCR output into it yet.

**Do:** wire the OCR result into `Document.search_text` so the existing
`trg_document_search_vector` trigger picks it up. Confirm the `case_id IN accessible_cases` filter
is applied on every query path — no exceptions.

**Files:** `backend/app/services/search_service.py`,
`backend/app/services/document_service.py`, `feature_plans/search_plan.md`.

**Done when:** a word that exists only inside a scanned image returns that document, and only for
users on that case.

---

## 8. `[P1]` Step-up MFA before sensitive actions

**Claim (slide 2):** *"The session token is verified on every single request, and re-checked
before sensitive actions."*

**Now:** nothing implements this. `auth_plan.md` verifies TOTP once at login and issues an 8h
token. **This is a new requirement created by the deck.**

**Do:**

1. Define the sensitive set — suggested: sign a document, create a share link, delete a document,
   create/deactivate a user, change a role.
2. Add a `@require_recent_mfa(minutes=15)` decorator in `backend/app/core/rbac.py` (next to
   `require_roles`). Put an `mfa_at` claim in the JWT at issue time; if `now - mfa_at > window`,
   return `401` with a distinguishable code (e.g. `MFA_REQUIRED`) so the frontend can prompt for a
   fresh code rather than logging the user out.
3. Add `POST /auth/mfa/step-up` that takes a TOTP code and returns a re-stamped token.

> If you decide not to build this, tell me and I will soften the slide-2 card to
> *"verified on every request"* and drop the step-up half of the sentence. Do not leave the claim
> on the slide unimplemented — it is exactly the kind of detail a judge probes.

**Files:** `backend/app/core/rbac.py`, `backend/app/core/security.py`,
`backend/app/blueprints/auth.py`, `feature_plans/auth_plan.md`, `frontend/src/hooks/useAuth.ts`.

**Done when:** signing a document with a 20-minute-old session prompts for a code instead of
succeeding.

---

## 9. `[P1]` Sharing becomes recipient-bound

**Claim (slide 2):** *"Time-limited, revocable access for a named recipient — not an open link.
Every access is recorded against the document it opened."* The review was explicit: **do not
market "no account needed" as a security feature.**

**Now:** `document_sharing_plan.md` has `allowed_email` as **optional**, and its own text admits
the email gate "is a convenience gate, not a security control."

**Do:**

1. Make `allowed_email` **required** in `ShareCreateSchema` — no anonymous links in the prototype.
2. Keep the existing atomic `use_count` increment; keep the 48h cap; keep revocation.
3. Update the plan's own security note: an email gate does not stop forwarding. If you want to
   claim genuine recipient binding, add a one-time code sent out of band, or accept the weaker
   claim and word the slide as "restricted to a named recipient".
4. Every access already writes `SHARE_LINK_ACCESSED` — verify it captures IP and user agent.

**Files:** `backend/app/schemas/sharing_schemas.py`,
`backend/app/services/sharing_service.py`, `feature_plans/document_sharing_plan.md`.

**Done when:** creating a share without a recipient email returns 400.

---

## 10. `[P1]` Make the audit trail append-only at the database level

**Claim (slide 2 + 4):** *"Each record is chained to the one before it, so a retroactive edit
fails verification"* — and slide 4 puts *"a privileged account rewriting the whole audit chain"*
under **partially addressed**, which is only honest if the easy path is actually closed.

**Now:** `audit_trail_plan.md` specifies `REVOKE UPDATE, DELETE ON audit_events FROM dms_app_user`
but there is no migration doing it.

**Do:**

1. Add the `REVOKE` to an Alembic migration so it is applied on every fresh database, not left as
   a manual step.
2. Make `/audit/verify` return `first_break_at` — the deck says verification *"names the first
   failing event"*, so it has to name it, not just return a boolean.
3. Keep `pg_advisory_xact_lock` even though the prototype runs a single Flask process. It costs
   nothing now and is the answer to the chain-forking question.

**Files:** `backend/migrations/` (new revision), `backend/app/services/audit_service.py`,
`backend/app/blueprints/audit.py`.

**Done when:** `UPDATE audit_events SET ...` as the app user is refused by PostgreSQL, and
`/audit/verify` on a hand-tampered row returns that row's id.

---

## 11. `[P1]` The tamper demo has to be a real, repeatable thing

**Claim:** it is named as **"the demo"** on slide 3 and referenced on slides 2, 4 and 5.

**Now:** `docs/EDGE_CASES.md` has it as step 5 of the smoke test. There is no script.

**Do:** add `backend/scripts/demo_tamper.py` that runs the whole arc unattended:

```
1. upload a known file to a known case      -> print document_id, chunk count, integrity hash
2. download it, checksum it                 -> assert byte-identical to the original
3. corrupt one chunk object on Server B     -> print which chunk, and the byte changed
4. download again                           -> assert HTTP 422, assert 0 bytes received
5. read the audit trail                     -> assert an INTEGRITY_VIOLATION row exists
6. print a clean before/after summary
```

Step 4's assertion that **zero bytes** arrive is the single most important line in the repo — it
is the claim the whole deck rests on. Make it a real test in `backend/tests/` too, not only a
demo script.

**Files:** `backend/scripts/demo_tamper.py` (new), `backend/tests/test_download_tamper.py` (new),
`docs/EDGE_CASES.md`.

**Done when:** one command produces the five-step output, and it passes in CI.

---

## 12. `[P1]` Benchmarks — the deck promises numbers

**Claim (slide 5):** three targets stated with a method, explicitly *"figures reported from the
prototype, not claimed now."* That is a promise to measure.

**Now:** nothing measures anything.

**Do:** add `backend/scripts/bench.py` writing `docs/BENCHMARKS.md`:

| Measure | Sizes | Record |
|---|---|---|
| Upload | 10 / 100 / 500 MB | wall time, encryption time, peak RSS, storage overhead vs plaintext |
| Retrieval | same | authorisation, verification, decryption, total |
| Tamper response | 1 corrupt chunk | detection time, **bytes served after failure (must be 0)** |
| Concurrency | 1 / 5 / 10 users | only what you actually ran |

Never publish a concurrency number you did not test. If 500 MB does not hold, that is a finding —
report it and fix §3 instead of quietly dropping the row.

**Files:** `backend/scripts/bench.py` (new), `docs/BENCHMARKS.md` (new).

---

## 13. `[P2]` Add the threat model as a document

**Claim (slide 4):** a three-column threat model — defended / partially addressed / out of scope.

**Now:** `docs/SECURITY.md` has a threat table but no scope boundary, and nothing says what the
prototype explicitly does *not* defend against.

**Do:** create `docs/THREAT_MODEL.md` with exactly the three columns from slide 4, so the deck and
the repo cannot drift. Copy them verbatim from the slide.

**Defended:** metadata-server compromise alone · chunk-store compromise alone · a DBA reading
evidence content · stolen credentials without the second factor · cross-case and unauthorised API
access · modification of stored ciphertext · retroactive edits to the audit trail

**Partially addressed:** application-server compromise · KMS or master-key compromise · a stolen
live session · backup media · a privileged account rewriting the whole chain

**Out of scope:** full root/OS compromise · physical access · a compromised crypto library ·
formal verification · production DR and HA · certified PKI / e-signature deployment

**Files:** `docs/THREAT_MODEL.md` (new), `docs/SECURITY.md` (link to it).

---

## 14. `[P2]` Terminology sweep

The review was blunt about wording. These strings should not survive anywhere in the repo:

| Replace | With | Where it currently appears |
|---|---|---|
| "blockchain-lite", "blockchain-grade" | "hash-chained, tamper-evident" | `docs/ARCHITECTURE.md`, `feature_plans/audit_trail_plan.md`, `codebase/DEFINITIONS.md` |
| "immutable audit" | "tamper-evident audit" | same |
| "zero-trust" | "least-privilege" | `docs/ARCHITECTURE.md` |
| "MinIO" as present tense | "the chunk store (MinIO in production)" | `models/document.py` and `models/document_chunk.py` docstrings both still open with "the actual bytes live … in MinIO" — they live on local disk today |
| "legally valid", "court-admissible" | "cryptographically signed; legal admissibility is out of scope" | `feature_plans/digital_signatures_plan.md` |
| ICJS / eSakshya / CCTNS positioning | *(remove — PRAMAAN is standalone)* | check `CLAUDE.md` |

Also rename the product to **PRAMAAN** in `README.md`, `CLAUDE.md` and `docs/ARCHITECTURE.md`.

---

## 15. `[P2]` Realign `docs/TODO.md` with the deck's build plan

Slide 4 shows six phases, not eight, and OCR moved into Day 6:

```
DAYS 1–2   Auth · MFA · RBAC
DAYS 3–4   Chunked crypto  ★
DAY 5      Audit chain
DAY 6      Search · OCR
DAYS 7–8   Signatures · sharing
DAY 9      Tamper demo · hardening
```

Update `docs/TODO.md` to match, and move the OCR block out of "FUTURE ROADMAP" into Phase 6.

Also correct Phase 3's download step 2, which still says *"Fetch master key from Vault"* — the
prototype uses the local file KMS.

---

## 16. Quick checklist

```
[ ]  1. Chunk store on a second host, own credentials
[ ]  2. KMS boundary decided; dedicated KMS_WRAPPING_KEY (stop reusing SECRET_KEY)
[ ]  3. Upload cap aligned — 500 MB in code, or 100 MB on the slides  ← DECISION
[ ]  4. Opaque chunk storage keys; ordering only in the DB
[ ]  5. Zustand + Axios removed from package.json and src/
[ ]  6. OCR in prototype scope, no Celery, five Indic packs, confidence gating
[ ]  7. OCR text reaches search_text and is case-scoped
[ ]  8. Step-up MFA on sensitive actions   ← or soften the slide
[ ]  9. allowed_email required on share creation
[ ] 10. REVOKE UPDATE/DELETE in a migration; /audit/verify returns first_break_at
[ ] 11. demo_tamper.py + a test asserting 0 bytes served
[ ] 12. bench.py + BENCHMARKS.md with real figures
[ ] 13. docs/THREAT_MODEL.md
[ ] 14. Terminology sweep + rename to PRAMAAN
[ ] 15. TODO.md phases match slide 4
```

---

## 17. Two things I could not decide for you

1. **Upload cap (§3)** — 500 MB on the slides vs 100 MB in `.env.example`. Tell me which way and
   I will make the other side match.
2. **Step-up MFA (§8)** — it is on the slide but was never in any plan. Either build it or let me
   reword the card. Leaving it as-is is the one option I would not take.
