# Feature Plan: Chunked Encrypted Document Storage

## What Is This Feature?

This is the core technical innovation of the entire system. Instead of storing a document as a single file on disk, the system:

1. Splits the document into fixed-size binary chunks (1 MB each)
2. Encrypts each chunk independently with a unique derived key
3. Stores each chunk as a separate object in MinIO (S3-compatible object storage)
4. Stores only metadata (chunk index, IV, auth tag, hash, MinIO path) in PostgreSQL
5. Stores the master document key in HashiCorp Vault (never in DB or MinIO)
6. On retrieval: fetches all chunks, decrypts each, verifies integrity, and streams the reconstructed file

**The result:** A compromised database gives an attacker only metadata. A compromised MinIO server gives an attacker only ciphertext. A compromised Vault gives an attacker only keys with no ciphertext. All three must be compromised simultaneously to access any document — and even then, the integrity check will detect tampering.

---

## Why Chunking Instead of Single-File Encryption?

| Approach | Problem |
|----------|---------|
| Single-file encryption | Encrypt once, store as one blob. One key compromise = entire file exposed. No streaming — must buffer entire file in RAM. |
| Chunked encryption | Each chunk has a derived key. Compromising one chunk's key does not help decrypt others. Supports streaming (process one chunk at a time). Supports partial retrieval in future. Enables per-chunk integrity verification. |

For a 500 MB forensic video, single-file encryption requires 500 MB of RAM. Chunked streaming requires only 1 MB at a time.

---

## Cryptographic Design — Every Detail

### Key Hierarchy

```
Vault
└── secret/docs/{document_id}/master_key   ← 32 random bytes, never leaves Vault

For each chunk i:
  chunk_key_i = HKDF-SHA256(
    IKM  = master_key,
    salt = document_id.encode('utf-8'),     ← ties key to this document
    info = f"chunk-{i}".encode('utf-8'),    ← ties key to this chunk index
    length = 32
  )
```

Why HKDF instead of just master_key XOR chunk_index?
- HKDF is a standard (RFC 5869) key derivation function designed specifically for this use case
- Provides cryptographic independence between chunk keys — knowing chunk_key_3 tells you nothing about chunk_key_7
- Salt binds the derived key to this specific document — same chunk index on a different document produces a completely different key

### Per-Chunk Encryption

```
For chunk i with plaintext bytes P:
  iv_i       = os.urandom(12)               ← 96-bit nonce, unique per chunk
  aesgcm     = AESGCM(chunk_key_i)
  ciphertext = aesgcm.encrypt(iv_i, P, authenticated_data=None)
             ← AESGCM.encrypt returns ciphertext + 16-byte auth tag concatenated

  chunk_hash = SHA256(ciphertext)           ← hash of the ciphertext (not plaintext)

  stored in MinIO: ciphertext (includes auth tag at end)
  stored in DB:    iv_i (hex), chunk_hash (hex), chunk_index, size_bytes, minio_key
```

Why store `chunk_hash`?
- Detects storage corruption or tampering before decryption is even attempted
- GCM auth tag also detects tampering during decryption — but verifying the hash first lets us fail fast without the Vault key lookup

### Document-Level Integrity

```
After all chunks are processed:
  integrity_hash = SHA256(
    chunk_hash_0 || chunk_hash_1 || ... || chunk_hash_n
  )
  where || means byte concatenation

Stored in documents.integrity_hash

On download: recompute this hash from fetched chunk hashes.
If it doesn't match: the document has been tampered with or chunks reordered.
Abort. Do not send a single byte to the client.
```

---

## Upload Flow — Step by Step

### API Endpoint

```
POST /api/v1/cases/{case_id}/documents
Content-Type: multipart/form-data
Authorization: Bearer <access_token>

Form fields:
  file:     <binary file data>
  doc_type: "FIR" | "CHARGE_SHEET" | "FORENSIC_REPORT" | "WITNESS_STATEMENT" |
            "COURT_FILING" | "EVIDENCE_RECORD" | "LEGAL_NOTICE" | "JUDGMENT" | "OTHER"
  title:    (optional) human-readable title
```

### Server Processing

```python
# Pseudocode — actual implementation in services/document_service.py

def upload_document(case_id, file_stream, filename, mime_type, doc_type, uploader_id):

    # Step 1: Validate
    assert mime_type in ALLOWED_MIME_TYPES       # pdf, docx, xlsx, jpg, png, tiff, mp4
    assert file.content_length <= MAX_FILE_SIZE  # 500 MB

    # Step 2: Create document record (status=UPLOADING)
    doc_id = uuid4()
    document = Document(
        id=doc_id, case_id=case_id,
        filename=filename, mime_type=mime_type,
        doc_type=doc_type, uploaded_by=uploader_id,
        status="UPLOADING"
    )
    db.session.add(document)
    db.session.flush()  # get doc_id without committing

    # Step 3: Generate master key, store in Vault
    master_key = secrets.token_bytes(32)
    vault_client.secrets.kv.v2.create_or_update_secret(
        path=f"docs/{doc_id}/master_key",
        secret={"value": master_key.hex()}
    )

    # Step 4: Chunk, encrypt, upload
    chunk_index = 0
    chunk_hashes = []
    total_bytes = 0

    while True:
        chunk_data = file_stream.read(CHUNK_SIZE)  # 1 MB
        if not chunk_data:
            break

        # Derive chunk key
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=str(doc_id).encode(),
            info=f"chunk-{chunk_index}".encode()
        )
        chunk_key = hkdf.derive(master_key)

        # Encrypt
        iv = os.urandom(12)
        aesgcm = AESGCM(chunk_key)
        ciphertext = aesgcm.encrypt(iv, chunk_data, None)
        # ciphertext = encrypted_bytes + 16-byte auth_tag

        # Hash ciphertext
        chunk_hash = hashlib.sha256(ciphertext).hexdigest()
        chunk_hashes.append(chunk_hash)

        # Upload to MinIO
        minio_key = f"doc-chunks/{doc_id}/chunk_{chunk_index:06d}"
        minio_client.put_object(
            bucket_name="doc-chunks",
            object_name=minio_key,
            data=BytesIO(ciphertext),
            length=len(ciphertext)
        )

        # Record chunk metadata
        chunk_record = DocumentChunk(
            document_id=doc_id,
            chunk_index=chunk_index,
            minio_key=minio_key,
            iv_hex=iv.hex(),
            chunk_hash=chunk_hash,
            size_bytes=len(chunk_data)  # plaintext size
        )
        db.session.add(chunk_record)

        total_bytes += len(chunk_data)
        chunk_index += 1

    # Step 5: Compute integrity hash
    combined = "".join(chunk_hashes).encode()
    integrity_hash = hashlib.sha256(combined).hexdigest()

    # Step 6: Update document record
    document.total_chunks = chunk_index
    document.file_size_bytes = total_bytes
    document.integrity_hash = integrity_hash
    document.status = "ACTIVE"

    db.session.commit()

    # Step 7: Audit
    audit_service.record(
        AuditEventType.DOCUMENT_UPLOADED,
        actor_user_id=uploader_id,
        target_type="document",
        target_id=doc_id,
        case_id=case_id,
        metadata={"filename": filename, "size_bytes": total_bytes, "chunks": chunk_index}
    )

    return document
```

### What Happens If Upload Fails Mid-Way?

```
If an exception occurs at any point:
  1. Set document.status = "FAILED"
  2. Delete any MinIO objects already uploaded for this doc_id
     (minio_client.remove_objects with prefix "doc-chunks/{doc_id}/")
  3. Delete the Vault secret at docs/{doc_id}/master_key
  4. Rollback db.session
  5. Return 500

Celery cleanup task runs hourly:
  Find all documents with status="FAILED" or status="UPLOADING" for > 1 hour
  Clean up orphaned MinIO objects and Vault keys
```

---

## Download / Reconstruction Flow — Step by Step

### API Endpoint

```
GET /api/v1/documents/{document_id}/download
Authorization: Bearer <access_token>
```

### Server Processing

```python
def download_document(document_id, requesting_user_id):

    # Step 1: Load document metadata
    document = Document.query.get_or_404(document_id)
    if document.is_deleted:
        abort(404)

    # Step 2: Verify access
    if not case_service.user_has_access(requesting_user_id, document.case_id):
        audit_service.record(AuditEventType.UNAUTHORIZED_ACCESS_ATTEMPT, ...)
        abort(403)

    # Step 3: Load all chunk metadata (ordered by index)
    chunks = DocumentChunk.query.filter_by(document_id=document_id)\
                .order_by(DocumentChunk.chunk_index).all()

    if len(chunks) != document.total_chunks:
        abort(422, "Document is incomplete — chunks missing")

    # Step 4: Fetch master key from Vault
    vault_response = vault_client.secrets.kv.v2.read_secret_version(
        path=f"docs/{document_id}/master_key"
    )
    master_key = bytes.fromhex(vault_response["data"]["data"]["value"])

    # Step 5: Stream decrypted bytes
    def generate():
        running_hashes = []

        for chunk in chunks:
            # Fetch ciphertext from MinIO
            response = minio_client.get_object("doc-chunks", chunk.minio_key)
            ciphertext = response.read()

            # Verify ciphertext hash (fast tamper check before crypto)
            computed_hash = hashlib.sha256(ciphertext).hexdigest()
            if computed_hash != chunk.chunk_hash:
                raise IntegrityError(
                    f"Chunk {chunk.chunk_index} hash mismatch — storage tampering detected"
                )

            running_hashes.append(computed_hash)

            # Derive chunk key
            hkdf = HKDF(algorithm=hashes.SHA256(), length=32,
                        salt=str(document_id).encode(),
                        info=f"chunk-{chunk.chunk_index}".encode())
            chunk_key = hkdf.derive(master_key)

            # Decrypt — AESGCM.decrypt verifies auth tag automatically
            # Raises InvalidTag if ciphertext was modified
            iv = bytes.fromhex(chunk.iv_hex)
            aesgcm = AESGCM(chunk_key)
            plaintext = aesgcm.decrypt(iv, ciphertext, None)

            yield plaintext

        # Final integrity check (after all chunks streamed)
        computed_integrity = hashlib.sha256(
            "".join(running_hashes).encode()
        ).hexdigest()

        if computed_integrity != document.integrity_hash:
            # This means chunks were reordered or the document record was tampered
            raise IntegrityError("Document-level integrity check failed")
            # Note: we've already yielded chunks at this point — in production,
            # pre-verify integrity before streaming (see note below)

    return Response(
        generate(),
        headers={
            "Content-Disposition": f'attachment; filename="{document.filename}"',
            "Content-Type": document.mime_type,
            "X-Content-Type-Options": "nosniff"
        }
    )
```

**Important design note on streaming vs pre-verification:**
For the prototype, pre-verify integrity (fetch all chunks, check everything, then stream). This buffers the entire document in RAM but guarantees no partial file is sent. For production with large files (forensic videos), implement a two-pass approach: first pass to verify, second pass to stream.

---

## Database Schema

```sql
CREATE TABLE documents (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id           UUID NOT NULL REFERENCES cases(id) ON DELETE RESTRICT,
    filename          TEXT NOT NULL,
    original_filename TEXT NOT NULL,                    -- sanitized filename vs. original
    mime_type         TEXT NOT NULL,
    doc_type          TEXT NOT NULL,
    file_size_bytes   BIGINT NOT NULL,
    total_chunks      INTEGER NOT NULL,
    integrity_hash    TEXT NOT NULL,                    -- SHA256 of all chunk hashes
    status            TEXT NOT NULL DEFAULT 'UPLOADING',  -- UPLOADING | ACTIVE | FAILED | DELETED
    uploaded_by       UUID NOT NULL REFERENCES users(id),
    is_deleted        BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_by        UUID REFERENCES users(id),
    deleted_at        TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE document_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
    chunk_index     INTEGER NOT NULL,
    minio_key       TEXT NOT NULL,          -- full path in MinIO bucket
    iv_hex          TEXT NOT NULL,          -- 12-byte nonce, hex (24 chars)
    chunk_hash      TEXT NOT NULL,          -- SHA256(ciphertext), hex (64 chars)
    size_bytes      INTEGER NOT NULL,       -- plaintext chunk size
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_document_chunk UNIQUE (document_id, chunk_index)
);

-- Index for fast chunk lookup in order
CREATE INDEX idx_chunks_document_index
    ON document_chunks (document_id, chunk_index ASC);

-- Allowed document types
ALTER TABLE documents ADD CONSTRAINT chk_doc_type
    CHECK (doc_type IN (
        'FIR', 'POLICE_REPORT', 'INVESTIGATION_RECORD', 'WITNESS_STATEMENT',
        'CHARGE_SHEET', 'COURT_FILING', 'EVIDENCE_RECORD', 'FORENSIC_REPORT',
        'LEGAL_NOTICE', 'JUDGMENT', 'OTHER'
    ));

-- Allowed statuses
ALTER TABLE documents ADD CONSTRAINT chk_status
    CHECK (status IN ('UPLOADING', 'ACTIVE', 'FAILED', 'DELETED'));
```

---

## MinIO Configuration

```
Bucket: doc-chunks
  Access policy: PRIVATE (no public access)
  Versioning: disabled (we manage versions ourselves)
  Lifecycle: None (we never auto-delete — legal retention requirements)
  Encryption: server-side encryption disabled (we handle our own)

Object key format: doc-chunks/{document_id}/chunk_{index:06d}
  Example: doc-chunks/a1b2c3d4-1234-5678-abcd-ef1234567890/chunk_000000
                                                              chunk_000001
                                                              chunk_000023
```

Zero-padded 6-digit chunk index ensures lexicographic ordering == numeric ordering for debugging. MinIO does not guarantee retrieval order, so we always order by `chunk_index` from DB.

---

## Vault Configuration

```
Secret engine: KV v2 (key-value, versioned)
Path: secret/docs/{document_id}/master_key
Value: { "value": "<64-char hex string>" }

Access policy (Vault policy for backend service):
  path "secret/data/docs/*" {
    capabilities = ["create", "read", "delete"]
  }
  # No "list" — backend should never enumerate all document keys
```

For the prototype, use Vault dev mode or a simple env-var KMS stub:

```python
# core/kms.py — stub for prototype
import os, json
from pathlib import Path

class EnvKMS:
    """Prototype-only: stores keys in a local encrypted JSON file"""
    def __init__(self):
        self._store = {}

    def store_key(self, doc_id: str, key_bytes: bytes):
        self._store[doc_id] = key_bytes.hex()

    def get_key(self, doc_id: str) -> bytes:
        return bytes.fromhex(self._store[doc_id])

    def delete_key(self, doc_id: str):
        self._store.pop(doc_id, None)
```

Replace `EnvKMS` with `VaultKMS` by swapping the class — service layer doesn't change.

---

## Allowed File Types

```python
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",         # .xlsx
    "image/jpeg",
    "image/png",
    "image/tiff",
    "video/mp4",          # forensic video evidence
    "audio/mpeg",         # recorded statements
    "audio/wav",
}

MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB
CHUNK_SIZE    = 1  * 1024 * 1024   # 1 MB
```

File type is verified by reading magic bytes (using the `python-magic` library), NOT by trusting the Content-Type header or file extension.

```python
import magic
detected_mime = magic.from_buffer(file_stream.read(2048), mime=True)
file_stream.seek(0)
if detected_mime not in ALLOWED_MIME_TYPES:
    abort(400, "File type not permitted")
```

---

## marshmallow Schemas

```python
class DocumentUploadSchema(Schema):
    doc_type = fields.Str(required=True, validate=validate.OneOf([
        'FIR', 'POLICE_REPORT', 'INVESTIGATION_RECORD', 'WITNESS_STATEMENT',
        'CHARGE_SHEET', 'COURT_FILING', 'EVIDENCE_RECORD', 'FORENSIC_REPORT',
        'LEGAL_NOTICE', 'JUDGMENT', 'OTHER'
    ]))
    title = fields.Str(load_default=None, validate=validate.Length(max=255))

class DocumentMetadataSchema(Schema):
    id            = fields.UUID(dump_only=True)
    case_id       = fields.UUID(dump_only=True)
    filename      = fields.Str(dump_only=True)
    doc_type      = fields.Str(dump_only=True)
    file_size_bytes = fields.Int(dump_only=True)
    total_chunks  = fields.Int(dump_only=True)
    status        = fields.Str(dump_only=True)
    uploaded_by   = fields.UUID(dump_only=True)
    created_at    = fields.DateTime(dump_only=True)
    # NOTE: integrity_hash, iv values, chunk metadata — NEVER serialized to client
```

---

## Frontend Components

| Component | Description |
|-----------|-------------|
| `DocumentUploader` | Drag-and-drop zone; shows file name, size, type; validates client-side before upload; progress bar via XHR `onprogress` |
| `DocumentList` | Table of documents in a case; columns: name, type, size, uploaded by, date, actions |
| `DocumentActions` | Download button (triggers `GET /download`); Delete (with confirmation modal); View signatures |
| `UploadProgressModal` | Shows chunk upload progress (backend sends SSE or percentage in response) |

**What frontend does NOT do:**
- Decrypt anything (all crypto is server-side)
- Cache document bytes (no blob URLs stored beyond the current tab session)
- Read or display chunk metadata (that's internal)

---

## Security Considerations Specific to This Feature

1. **Filename sanitization** — strip all path components, limit to `[a-zA-Z0-9._-]`, max 255 chars. Store original filename separately from the sanitized one.
2. **MIME type validation** — read magic bytes server-side; never trust client header.
3. **Streaming upload** — do not `request.get_data()` (buffers entire file in RAM); use `request.stream`.
4. **MinIO object ACL** — bucket must be private; generate pre-signed URLs only for specific download flows, not for general access.
5. **No document content in logs** — log only doc_id, case_id, size, chunk count.
6. **Soft delete only** — `is_deleted=True` hides document from users but chunks remain in MinIO for legal audit. Physical deletion only allowed by SUPER_ADMIN via a separate administrative process.
7. **Orphan cleanup** — Celery task to detect and clean UPLOADING documents older than 1 hour (failed upload recovery).

---

## Edge Cases

| Scenario | Behaviour |
|----------|-----------|
| Vault/KMS unreachable during upload | Abort before writing any chunk; 503. Never fall back to DB/disk key storage. |
| Vault/KMS unreachable during download | 503; never serve a partially decrypted file. |
| MinIO write fails after some chunks uploaded | Roll back — delete uploaded objects + Vault key, mark `FAILED`, rollback DB. No orphans. |
| MinIO object missing / deleted out-of-band | Fetch error or `total_chunks` mismatch → 422 INTEGRITY_VIOLATION (audited). |
| Ciphertext modified in MinIO | `SHA256(ciphertext) != chunk_hash` or GCM `InvalidTag` → 422 before any byte is streamed. |
| Chunk rows reordered / index tampered | Overall `integrity_hash` won't match → 422. |
| Empty (0-byte) file | Rejected at validation (min 1 byte) — a 0-chunk document is invalid. |
| Extension lies about type (`.pdf` that is an `.exe`) | Magic-byte MIME check rejects it. |
| Client disconnects mid-upload | Document stuck `UPLOADING`; hourly Celery sweep purges it (objects + key + rows) after 1h. |
| Access token expires mid-download | Auth is checked once at request start; a long transfer completes. |
| Duplicate identical file | Prototype stores two independent documents (dedup is roadmap R3). |

See `docs/EDGE_CASES.md` for the system-wide catalog and the pre-demo smoke test.

---

## Performance Considerations

| Concern | Approach |
|---------|---------|
| Large file upload | Stream directly to chunker; never buffer full file |
| Many chunks to download | Fetch chunks concurrently (ThreadPoolExecutor, max ~4 workers) |
| MinIO latency | MinIO runs locally in Docker — negligible for prototype |
| DB writes per chunk | Use `db.session.bulk_save_objects()` for chunk records |
| Pre-verify buffers whole doc in RAM | Fine for prototype file sizes; production uses two-pass streaming re-reading from MinIO |

---

## Testing Plan

```
tests/documents/
├── test_upload.py
│   ├── test_upload_pdf_creates_chunks_in_minio
│   ├── test_upload_stores_correct_chunk_count
│   ├── test_upload_integrity_hash_computed_correctly
│   ├── test_upload_rejected_invalid_mime_type
│   ├── test_upload_rejected_file_too_large
│   ├── test_upload_requires_case_access
│   ├── test_failed_upload_cleans_up_minio_objects
│   └── test_failed_upload_cleans_up_vault_key
├── test_download.py
│   ├── test_download_reconstructs_exact_original_bytes
│   ├── test_download_rejects_unauthorized_user
│   ├── test_download_fails_on_tampered_chunk (modify MinIO object)
│   ├── test_download_fails_on_wrong_chunk_order (swap chunk_index in DB)
│   ├── test_download_fails_on_missing_chunk
│   ├── test_download_fails_on_integrity_hash_mismatch
│   └── test_download_creates_audit_event
├── test_crypto.py
│   ├── test_hkdf_different_indices_produce_different_keys
│   ├── test_hkdf_same_inputs_produce_same_key (deterministic)
│   ├── test_aes_gcm_encrypt_decrypt_roundtrip
│   ├── test_aes_gcm_detects_ciphertext_modification
│   └── test_aes_gcm_detects_iv_modification
```

---

## Implementation Order

1. `backend/app/core/crypto.py` — HKDF, AES-256-GCM encrypt/decrypt functions
2. `backend/app/core/kms.py` — KMS abstraction (EnvKMS stub, VaultKMS for later)
3. `backend/app/storage/minio_client.py` — MinIO connection + put/get/delete helpers
4. `backend/app/models/document.py` + `document_chunk.py` — SQLAlchemy models
5. `backend/app/schemas/document_schemas.py` — marshmallow schemas
6. `backend/app/services/document_service.py` — `upload_document()`, `download_document()`
7. `backend/app/blueprints/documents.py` — Flask routes
8. Celery orphan cleanup task
9. Frontend: `DocumentUploader` + `DocumentList` components
10. Tests — especially `test_crypto.py` and `test_download.py` tamper tests
