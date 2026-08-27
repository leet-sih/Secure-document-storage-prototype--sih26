# Future Feature Roadmap — Secure DMS (leet / SIH26)

> **This is a reference document only** — no code changes. Use this for presentations, pitches,
> and stakeholder discussions to show where the system goes after the prototype.
>
> All features below are post-prototype / post-hackathon. The prototype covers the core DMS
> (chunked encrypted storage, audit chain, RBAC, MFA, cases, documents, search, signatures,
> sharing).

---

## 1. OCR-Based Document Digitisation

**What it does:** Scanned physical documents (FIRs, charge sheets, court filings) are
photographed or scanned and uploaded. The system runs OCR to extract searchable text, making
legacy paper records fully retrievable.

**Why it matters:** Law enforcement agencies in India still handle large volumes of paper
documents. Digitisation with OCR brings them into the secure DMS without manual re-typing.

**Key components:**
- **Tesseract OCR** — open-source engine; runs entirely on-premise (no cloud API, no data
  leakage)
- **Pre-processing pipeline** — deskew, denoise, binarise, contrast-boost before OCR for
  accuracy on low-quality scans
- **Confidence gating** — OCR results below a threshold (e.g. 80%) are flagged for manual
  review; not silently accepted
- **Extracted text stored as metadata** — text goes into the document's `search_vector`
  (PostgreSQL FTS); the original scanned image is stored encrypted in the chunk store as-is
- **Audit trail** — `OCR_COMPLETED` / `OCR_FLAGGED` events recorded; reviewer sign-off tracked

**Tech:** Tesseract 5, OpenCV (pre-processing), Pillow, Celery task (async — OCR can take 10s+)

---

## 2. Secure Session Playground (AI Document Summarisation)

**What it does:** An officer opens a secured, ephemeral session to get an AI-generated summary
of a document. The session is sandboxed — no data leaves the server, no summary is stored unless
explicitly saved, and the session self-destructs on timeout.

**Why it matters:** Reading 200-page charge sheets before a hearing is impractical. AI
summarisation inside a secure boundary gives officers actionable context without exposing
document content to third-party cloud APIs.

**Key components:**
- **Local LLM (Ollama + Mistral 7B)** — model runs on-device; document text never leaves the
  backend server
- **Ephemeral session container** — each summarisation session runs in an isolated context; no
  disk writes; wiped on close or 30-min timeout
- **Document bytes decrypted in-memory** — master key fetched from KMS, document decrypted in a
  RAM buffer, fed to the LLM context; buffer zeroed after session
- **Explicit save gate** — user must actively choose to save a summary as a case note; no
  automatic persistence
- **Audit events** — `PLAYGROUND_SESSION_OPENED`, `PLAYGROUND_SESSION_CLOSED`,
  `PLAYGROUND_SUMMARY_SAVED`
- **Role restriction** — CASE_OFFICER, INVESTIGATOR, PROSECUTOR only

**Tech:** Ollama (model runner), Mistral 7B or Phi-3-mini (local model), Docker-in-Docker
session isolation (production), Redis session TTL

---

## 3. AI-Based Semantic Document Retrieval

**What it does:** Officers can search documents using natural-language queries ("show me all FIRs
mentioning theft near railway stations in 2024") instead of only keyword or metadata search.
Results are ranked by semantic relevance.

**Why it matters:** Keyword search misses synonyms, context, and cross-document connections.
Semantic search surfaces related documents that keyword search would miss — critical for building
case narratives across thousands of records.

**Key components:**
- **Embedding pipeline** — after OCR or text extraction, document text is chunked and embedded
  using `all-MiniLM-L6-v2` (a small, fast sentence-transformer model)
- **Vector database (Qdrant)** — stores embeddings; supports filtered approximate nearest-
  neighbour search (ANN). Vectors are tied to document IDs, not the text itself
- **Hybrid search** — BM25 keyword score + vector similarity re-ranking; gives the best of
  both worlds
- **Access-scoped results** — the vector search is post-filtered by the user's accessible cases;
  a query never surfaces documents the user isn't authorised to see
- **Privacy by design** — search queries are never logged with their results; only
  `SEARCH_PERFORMED` + result count is recorded in the audit trail

**Tech:** sentence-transformers (`all-MiniLM-L6-v2`), Qdrant, rank-fusion (RRF algorithm),
Celery for async embedding jobs

---

## 4. Production Infrastructure Upgrade

**What it does:** Replace the prototype's local-disk/in-memory components with scalable,
fault-tolerant production services — no changes to security mechanisms or document flows.

**Why it matters:** The prototype handles one team demo; production must handle multiple
agencies, concurrent uploads, multi-worker Flask, and survive a service restart.

| Prototype (now) | Production (planned) | What changes |
|-----------------|----------------------|--------------|
| Local disk `./data/chunks` | **MinIO / S3** object storage | `storage/chunk_store.py` — same interface |
| Local file `./data/keys` | **HashiCorp Vault** | `core/kms.py` — same interface |
| 8h JWT in localStorage | 15-min access + **httpOnly refresh cookie** (Redis-backed rotation) | `core/security.py`, frontend auth |
| In-memory rate limiting | **Redis**-backed limiter + TOTP replay guard | `extensions.py`, `core/totp.py` |
| On-demand cleanup function | **Celery + beat** (also drives OCR and embedding jobs) | `tasks/` |
| `flask run` (single process) | **Gunicorn** (multi-worker) + **Nginx** (TLS, HSTS, CSP) | `Dockerfile`, `infra/` |

---

## 5. Multi-Agency Federation

**What it does:** Cases and documents can be securely shared across agency boundaries (e.g. state
police sharing evidence with the CBI or a High Court) with explicit consent, time-limited access,
and a cross-agency audit trail.

**Why it matters:** Investigations often span jurisdictions. Currently evidence exchange is ad-hoc
(email, physical courier). A federated DMS creates a verifiable chain of custody across agencies.

**Key components:**
- Agency-level identity (not just user-level): each agency gets its own signing key
- Cross-agency share tokens: time-boxed, revocable, Ed25519-signed by the sharing agency
- Federated audit: the receiving agency's read events are pushed back to the originating
  agency's audit chain
- Data residency controls: document bytes stay in the originating agency's chunk store; only
  decrypted content crosses the wire over mTLS

---

## 6. Mobile Officer App (Read-Only Field Access)

**What it does:** A mobile app for field officers to view case summaries and download specific
documents for offline use — with automatic expiry and remote wipe.

**Why it matters:** Investigating officers in the field can't always carry laptops to access
case files. A hardened mobile client with offline capability and remote wipe closes this gap.

**Key components:**
- React Native (iOS + Android) — shared codebase with the web frontend's API layer
- Offline document cache — documents downloaded to the device are encrypted at rest using the
  device's secure enclave key
- Remote wipe — an admin can revoke a device token; next sync deletes the local encrypted cache
- Biometric unlock — Face ID / fingerprint replaces the TOTP step on mobile

---

## 7. Tamper-Evident Export & Court Filing

**What it does:** Generate a sealed, verifiable export package of a case's documents and audit
trail for submission to a court or external authority — a PDF bundle with embedded Ed25519
signatures and a chain-of-custody certificate.

**Why it matters:** Courts need to verify that evidence hasn't been altered since collection.
The export package provides a cryptographically verifiable chain of custody without requiring the
court to access the DMS directly.

**Key components:**
- Case export endpoint: assembles document binaries + metadata + audit events for a date range
- Chain-of-custody certificate: PDF signed by the CASE_OFFICER's Ed25519 key, listing every
  action on each document (upload, download, signature, share)
- Verification tool: a standalone Python script that any party can run to verify the signatures
  and integrity hashes without installing the full system
- Audit event: `CASE_EXPORTED_FOR_COURT`

---

*This roadmap is directional, not a commitment. Priorities will shift based on stakeholder
feedback after the prototype demo. The prototype's clean interfaces (chunk_store, kms, audit
service) are deliberately designed so each of these features slots in without rewriting the core.*
