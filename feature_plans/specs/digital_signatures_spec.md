# Spec: Digital Signatures

## What This Feature Does

Every document in PRAMAAN carries Ed25519 cryptographic signatures that prove:
1. **Who uploaded it** — the uploader's signature is recorded automatically on upload (auto-sign).
2. **Who else approved it** — any authorized case member can voluntarily sign a document to indicate review/approval.
3. **That it has not been tampered with since signing** — if the document's chunks are altered after signing, verification fails and shows the document as modified.

Ed25519 keys are generated per-user on first sign action. The raw private key is AES-256-GCM
wrapped with `SECRET_KEY` (domain-separated from TOTP via a distinct HKDF `info` tag) and stored in
`users.signing_private_key_enc`. The public key is stored in `users.signing_public_key` (safe unencrypted).

In production, private keys would live in HashiCorp Vault. For the prototype, the encrypted column
is the agreed approach (same threat model as TOTP secrets).

---

## Exact Files Modified

| File | Change |
|------|--------|
| `backend/app/core/signing.py` | Implement `generate_keypair`, `sign`, `verify`; add `encrypt_private_key`, `decrypt_private_key` |
| `backend/app/models/user.py` | Add `signing_private_key_enc` column |
| `backend/app/services/signature_service.py` | Implement `sign_document`, `verify_signatures`, `revoke_signature` |
| `backend/app/schemas/signature_schemas.py` | Add nested signer, `VerifyResultSchema`, `VerifyResponseSchema` |
| `backend/app/blueprints/signatures.py` | Implement 4 routes |
| `backend/app/blueprints/documents.py` | Auto-sign after upload (best-effort, never fails the upload) |
| `backend/app/__init__.py` | Register `signatures_bp` |
| `backend/migrations/versions/002_signatures.py` | Add `signing_private_key_enc` to users; create `document_signatures` |

---

## Data Model Changes

### `users` table — new column
```sql
ALTER TABLE users ADD COLUMN signing_private_key_enc TEXT;
-- hex(iv || ciphertext+tag) of the raw Ed25519 private key, AES-256-GCM wrapped with SECRET_KEY
```

### `document_signatures` table — new
```sql
CREATE TABLE document_signatures (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id             UUID NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
    signer_user_id          UUID NOT NULL REFERENCES users(id),
    integrity_hash_at_signing TEXT NOT NULL,  -- snapshot of integrity_hash at sign time
    signed_payload_hash     TEXT NOT NULL,    -- SHA256(integrity_hash|doc_id|signer_id|ts)
    signature_hex           TEXT NOT NULL,    -- 128-char hex Ed25519 signature
    is_valid                BOOLEAN,          -- NULL until first verify
    last_verified_at        TIMESTAMPTZ,
    revoked_at              TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_one_sig_per_user_per_doc UNIQUE (document_id, signer_user_id)
);
```

---

## API Contract

### POST /api/v1/documents/{id}/sign
**Roles:** `SUPER_ADMIN`, `CASE_OFFICER`, `INVESTIGATOR`  
**Body:** none (identity from JWT)  
**201:** `SignatureResponseSchema`  
**409:** already signed / case is ARCHIVED  
**404:** document not found or user not a case member

### GET /api/v1/documents/{id}/signatures
**Roles:** any authenticated case member  
**200:** `{ "document_id": uuid, "signatures": [SignatureResponseSchema] }`  
**404:** document not found or not a member

### POST /api/v1/documents/{id}/signatures/verify
**Roles:** any authenticated case member  
**200:** `{ "document_id": uuid, "verified_at": datetime, "results": [VerifyResultSchema] }`  
Re-runs Ed25519 verify on every signature + checks `integrity_hash` match.  
Updates `is_valid` and `last_verified_at` on each row.  
Records `SIGNATURE_VERIFIED` audit event.

### DELETE /api/v1/documents/{id}/signatures/{sig_id}
**Roles:** own signature only, or `SUPER_ADMIN`  
**204:** revoked  
**403:** not your signature  
**404:** signature not found  
**409:** already revoked  
Sets `revoked_at = now()` and `is_valid = False`. Row is kept (auditable).

---

## Security Threat Model

| Threat | Mitigation |
|--------|-----------|
| Attacker replaces document chunks after signing | `integrity_hash_at_signing` vs current `integrity_hash` mismatch is caught at verify time |
| Attacker swaps user's public key | Signature verification against the swapped key will fail (original signature was made with original private key) |
| Attacker replays an old document's signed payload against a different document | `signed_payload = SHA256(integrity_hash \| doc_id \| signer_id \| ts)` binds the signature to a specific document + signer + timestamp |
| Attacker modifies `created_at` in the DB | Timestamp is in the signed payload — changing it invalidates the signature |
| Private key compromise from DB | Private key is AES-256-GCM encrypted at rest; plaintext never touches disk unencrypted |
| Unauthenticated access | All routes require valid JWT access token (not MFA temp token) |
| Non-member signing a document | `sign_document` service checks `CaseMember.is_active` after RBAC gate; non-members get 404 |

---

## Edge Cases (cross-ref docs/EDGE_CASES.md)

- **Auto-sign failure on upload**: caught by `try/except`, logs, returns 201 without signature. Upload never fails due to signing.
- **Empty `signing_public_key`**: `verify_signatures` marks this signature invalid with reason "Signer public key not found".
- **Signing a deleted document**: service checks `doc.is_deleted` → 404.
- **Signing in an ARCHIVED case**: service checks `case.status == "ARCHIVED"` → 409.
- **Duplicate sign (same user, same doc)**: DB UNIQUE constraint catches it → 409 before any crypto work.
- **Revoked-then-verify**: `verify_signatures` short-circuits on `sig.revoked_at is not None` → `is_valid=False`.

---

## Review

### 1. Security holes?
No obvious holes. Key rotation is not implemented (if `signing_private_key_enc` is compromised, all past signatures can be forged in theory — acceptable for prototype; production would use HSM/Vault).

### 2. Contradictions with CLAUDE.md / SECURITY.md?
None. The spec uses `encrypt_string`/`decrypt_string` from `core/crypto.py` (the only module allowed to do crypto). RBAC is enforced at API layer. Audit events are recorded for all three actions.

### 3. Simpler design?
Could skip auto-sign on upload; manual-only is simpler. But the user explicitly requested auto-sign, so it's included as best-effort.

### 4. Edge cases from docs/EDGE_CASES.md?
Covered: empty file scenario doesn't apply (no content read); deleted document → 404; ARCHIVED case → 409; non-member → 404.

### 5. Break existing features?
- `documents.py` is modified (add auto-sign call). Failure is caught and logged; the upload 201 response is unchanged. Low risk.
- No other files are modified. Migrations are additive only.
