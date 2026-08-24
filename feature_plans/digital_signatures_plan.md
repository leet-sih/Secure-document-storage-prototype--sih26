# Feature Plan: Digital Signatures

## What Is This Feature?

Digital signatures allow authorized users to cryptographically sign a document, proving that:
1. They have seen and approved the document
2. The document has not been modified since they signed it

Each signature is tied to the document's `integrity_hash` (the SHA-256 of all chunk hashes). If the document is tampered with after signing, the signature becomes invalid and the system reports this on verification.

This gives documents legal validity — a signed forensic report, charge sheet, or FIR can be verified to have been approved by a specific officer and not altered since approval.

---

## Why Ed25519?

| Algorithm | Key size | Sign time | Verify time | Security |
|-----------|----------|-----------|-------------|---------|
| RSA-2048 | 256 bytes | slow | fast | Good |
| RSA-4096 | 512 bytes | very slow | fast | Strong |
| ECDSA-256 | 32 bytes | fast | fast | Good |
| **Ed25519** | **32 bytes** | **very fast** | **very fast** | **Strong** |

Ed25519 (EdDSA on Curve25519) is the modern standard. It's:
- Used by OpenSSH, Signal, TLS 1.3
- Deterministic (no random nonce needed — no nonce reuse vulnerabilities like ECDSA)
- Constant-time implementation prevents timing attacks
- Python `cryptography` library supports it natively

---

## Key Generation & Storage

Each user gets one Ed25519 key pair, generated on first signature action.

```
User's first POST /documents/{id}/sign:
  Server generates: private_key, public_key = Ed25519PrivateKey.generate()
  private_key_bytes = private_key.private_bytes(
      encoding=Encoding.Raw,
      format=PrivateFormat.Raw,
      encryption_algorithm=NoEncryption()
  )
  → Encrypt private_key_bytes with AES-256-GCM using app SECRET_KEY before storing
  → Store encrypted_private_key in Vault at: secret/users/{user_id}/signing_key
  → Store public_key_bytes (raw, unencrypted) in users.signing_public_key column
    (public keys are safe to store unencrypted — they are meant to be public)
```

Why store private key in Vault and not let users hold it?
- This is a server-side signature scheme. Users don't manage keys — they press "Sign" and the server signs on their behalf using their stored key.
- For a production legal system, you'd use HSM (Hardware Security Module) or a client-side key stored on a smart card. For the prototype, Vault is the appropriate stub.
- The user must be authenticated (valid JWT + MFA) to trigger a signature, which means the authentication event is effectively the user's consent.

---

## What Gets Signed

```
signed_data = SHA256(
    document.integrity_hash +        ← covers all document content
    str(document.id) +               ← ties signature to this document
    signer_user_id +                 ← ties signature to this user
    timestamp.isoformat()            ← prevents replay (re-signing old data)
)

signature_bytes = private_key.sign(signed_data)
```

The `signed_data` input is a SHA-256 hash — Ed25519 can sign arbitrary byte strings, and pre-hashing is unnecessary (Ed25519 hashes internally), but we do it here to create a deterministic, unambiguous payload that encodes all relevant context.

---

## Database Schema

```sql
CREATE TABLE document_signatures (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
    signer_user_id      UUID NOT NULL REFERENCES users(id),
    integrity_hash_at_signing TEXT NOT NULL,  -- snapshot of integrity_hash at sign time
    signed_payload_hash TEXT NOT NULL,        -- SHA256(integrity_hash + doc_id + user_id + ts)
    signature_hex       TEXT NOT NULL,        -- Ed25519 signature, hex-encoded (128 chars)
    is_valid            BOOLEAN,              -- NULL until verified; TRUE/FALSE after check
    last_verified_at    TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_one_sig_per_user_per_doc UNIQUE (document_id, signer_user_id)
);

-- Add to users table
ALTER TABLE users ADD COLUMN signing_public_key TEXT;  -- hex-encoded Ed25519 public key
```

Why `integrity_hash_at_signing`?
- If the document is somehow modified (chunk swap, integrity_hash update in DB), the stored signature still references the old hash.
- Verification computes the current integrity_hash and compares it to `integrity_hash_at_signing`. A mismatch means the document was modified after signing — signature is invalidated.

Why `UNIQUE (document_id, signer_user_id)`?
- One signature per user per document. To re-sign, the user must explicitly revoke the old signature first. This prevents silent signature replacement.

---

## API Endpoints

### POST /api/v1/documents/{id}/sign `[SUPER_ADMIN, CASE_OFFICER, INVESTIGATOR]`

No request body needed. The user's identity comes from the JWT.

Server:
1. Load document — verify user has access to parent case
2. Check document is not deleted; check case is not ARCHIVED
3. Check user hasn't already signed this document (409 if so)
4. Load or generate user's Ed25519 private key from Vault
5. Build `signed_payload`:
   ```python
   ts = datetime.now(UTC).isoformat()
   payload_str = "|".join([
       document.integrity_hash,
       str(document.id),
       str(current_user.id),
       ts
   ])
   signed_data = hashlib.sha256(payload_str.encode()).digest()
   ```
6. Sign: `signature_bytes = private_key.sign(signed_data)`
7. Save `DocumentSignature` record
8. Record AuditEvent: DOCUMENT_SIGNED

```json
// Response 201
{
  "id": "uuid",
  "document_id": "uuid",
  "signer": { "id": "uuid", "full_name": "Arjun Sharma", "role": "INVESTIGATOR" },
  "signed_at": "2026-08-25T14:32:11Z",
  "is_valid": null   ← null until explicitly verified
}
```

### GET /api/v1/documents/{id}/signatures `[Case members]`

Returns all signatures for a document with their validity status.

```json
{
  "document_id": "uuid",
  "signatures": [
    {
      "id": "uuid",
      "signer": { "id": "uuid", "full_name": "Arjun Sharma", "role": "INVESTIGATOR" },
      "signed_at": "2026-08-25T14:32:11Z",
      "is_valid": true,
      "last_verified_at": "2026-08-25T15:00:00Z"
    },
    {
      "id": "uuid",
      "signer": { "id": "uuid", "full_name": "Priya Singh", "role": "CASE_OFFICER" },
      "signed_at": "2026-08-25T14:45:00Z",
      "is_valid": false,    ← document was modified after this signature
      "last_verified_at": "2026-08-25T15:00:00Z"
    }
  ]
}
```

### POST /api/v1/documents/{id}/signatures/verify `[Case members]`

Re-verifies all signatures for a document right now.

Server (for each signature):
1. Load signer's current `signing_public_key`
2. Recompute `signed_payload` using `integrity_hash_at_signing`, doc_id, signer_id, `created_at` from the signature record
3. `public_key.verify(signature_bytes, signed_data)` — raises `InvalidSignature` if tampered
4. Also compare: `document.integrity_hash == signature.integrity_hash_at_signing` — if they differ, document was modified after signing
5. Update `is_valid` and `last_verified_at` on each signature record
6. Record AuditEvent: SIGNATURE_VERIFIED

```json
// Response
{
  "document_id": "uuid",
  "verified_at": "...",
  "results": [
    { "signature_id": "...", "signer_email": "...", "is_valid": true },
    { "signature_id": "...", "signer_email": "...", "is_valid": false,
      "reason": "Document modified after signing" }
  ]
}
```

### DELETE /api/v1/documents/{id}/signatures/{sig_id} `[Own signature only, or SUPER_ADMIN]`

Revokes a signature. Only the signer can revoke their own signature (or SUPER_ADMIN).

Sets a `revoked_at` timestamp and `is_valid=false` on the record. Does NOT delete the record — the fact that it existed and was revoked is auditable.

---

## marshmallow Schemas

```python
class SignatureResponseSchema(Schema):
    id              = fields.UUID(dump_only=True)
    document_id     = fields.UUID(dump_only=True)
    signer          = fields.Nested(UserBriefSchema, dump_only=True)
    signed_at       = fields.DateTime(dump_only=True)
    is_valid        = fields.Bool(dump_only=True, allow_none=True)
    last_verified_at = fields.DateTime(dump_only=True, allow_none=True)
    # Never dump: signature_hex, signed_payload_hash, integrity_hash_at_signing
    # These are internal cryptographic values
```

---

## Frontend Components

| Component | Description |
|-----------|-------------|
| `SignaturePanel` | Displayed on document detail page; lists who signed, when, validity badge |
| `SignButton` | "Sign Document" button with confirmation modal: "You are signing this document as [name]. This action is recorded." |
| `SignatureBadge` | Compact: green "Signed ✓" or red "Invalid ✗" or grey "Unverified" |
| `VerifyAllButton` | "Verify Signatures" — triggers POST /signatures/verify, refreshes panel |
| `InvalidSignatureWarning` | Red alert: "This document was modified after [name] signed it on [date]." |

---

## Security Considerations

1. **Key compromise** — If Vault is compromised, attacker has all private keys. In production, use an HSM. For prototype, Vault is the agreed approach.
2. **Timestamp manipulation** — The `created_at` field in DB could be altered by a compromised DBA. We include it in the signed payload so that altering the timestamp would invalidate the signature.
3. **Public key swap** — If `users.signing_public_key` is altered, verification would fail (attacker's key doesn't match original signature). The audit trail records key generation, so a swap is detectable.
4. **Multiple signatories** — Multiple users can sign a document. All signatures are independent and individually verifiable.
5. **Post-signing modification** — Caught by comparing `integrity_hash_at_signing` vs current `integrity_hash`.

---

## Legal Validity Note

For the hackathon, this provides technical non-repudiation. For production legal validity in India:
- Would need to comply with the **Information Technology Act 2000**, Section 5 (Digital Signatures)
- Would require a Digital Signature Certificate (DSC) issued by a licensed Certifying Authority (CA)
- The prototype's Ed25519 scheme demonstrates the concept; DSC integration would replace the self-generated key pair

---

## Testing Plan

```
tests/signatures/
├── test_sign.py
│   ├── test_authorized_user_can_sign_document
│   ├── test_unauthorized_user_cannot_sign
│   ├── test_duplicate_signature_returns_409
│   ├── test_signing_creates_audit_event
│   └── test_signing_on_archived_case_blocked
├── test_verify.py
│   ├── test_unmodified_document_signature_is_valid
│   ├── test_modified_integrity_hash_invalidates_signature
│   ├── test_tampered_signature_hex_is_invalid
│   ├── test_swapped_public_key_detected
│   └── test_verify_updates_last_verified_at
├── test_revoke.py
│   ├── test_user_can_revoke_own_signature
│   ├── test_user_cannot_revoke_others_signature
│   ├── test_super_admin_can_revoke_any_signature
│   └── test_revoked_signature_still_in_db
```

---

## Implementation Order

1. `DocumentSignature` SQLAlchemy model + migration
2. Add `signing_public_key` to User model + migration
3. `backend/app/core/signing.py` — key generation, sign, verify helpers
4. `signature_service.py` — `sign_document()`, `verify_signatures()`, `revoke_signature()`
5. `signatures.py` Blueprint — POST /sign, GET /signatures, POST /verify, DELETE /{id}
6. Frontend: `SignaturePanel` + `SignButton` + `VerifyAllButton`
7. Tests
