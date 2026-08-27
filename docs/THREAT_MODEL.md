# Threat Model — PRAMAAN: Secure Evidence Vault (leet / SIH26)

> This table is the authoritative source for the three-column threat scope shown on slide 4.
> Keep this file and the slide in sync — do not let them drift.
> See `docs/SECURITY.md` and `docs/ARCHITECTURE.md` for implementation details.

---

## Defended

These threats are directly addressed by the prototype architecture.

| Threat | How it is defended |
|--------|--------------------|
| Metadata server (Server A / PostgreSQL) compromised alone | DB has only metadata + opaque chunk storage keys. No document content, no encryption keys. Storage keys are random 16-byte hex strings with no structure — not exploitable without the ciphertext AND the KMS. |
| Chunk store (Server B) compromised alone | Server B holds only flat, structureless ciphertext blobs. No document boundaries in filenames (opaque keys). No encryption keys on Server B. No DB access on Server B. Blobs are AES-256-GCM — unreadable without the per-chunk key. |
| A DBA reading evidence content | Database contains only metadata. Document content is encrypted and stored separately on Server B. A DBA with full PostgreSQL access cannot reconstruct any document. |
| Stolen credentials without the second factor | TOTP (6-digit, 30s window) is verified server-side before any token is issued. No way to skip MFA. |
| A live session used for sensitive actions after 15 minutes | Step-up MFA (`@require_recent_mfa`) re-checks TOTP before sign, share, delete, user management. A stolen 8h token cannot perform sensitive actions without the physical authenticator device. |
| Cross-case and unauthorised API access | Case-scoped RBAC on every endpoint. Non-members receive 404 (not 403) — the API does not confirm a case exists. |
| Modification of stored ciphertext | Per-chunk SHA-256 hash verified before decryption. GCM auth tag validated during decryption. Document-level integrity_hash re-checked over all chunks. Any modification → 422 + INTEGRITY_VIOLATION audit event. Zero bytes served to client. |
| Retroactive edits to the audit trail via the app user | `REVOKE UPDATE, DELETE ON audit_events FROM dms_app_user` applied in a migration. Hash chain detects any modification, deletion, or insertion — `GET /audit/verify` names `first_break_at`. |

---

## Partially Addressed

These threats have meaningful mitigations in the prototype but are not fully closed.

| Threat | Mitigation in prototype | Remaining gap |
|--------|------------------------|---------------|
| Application server compromise | Secrets in env vars (not code). KMS_WRAPPING_KEY, SECRET_KEY, JWT_SECRET are separate. In-memory key usage only. | A root-level attacker on the app host can read env vars and KMS_DIR. Production: Vault + HSM removes plaintext key exposure. |
| KMS or master-key compromise | KMS on app host, separate OS user. Master keys wrapped with dedicated KMS_WRAPPING_KEY (not shared with SECRET_KEY). | Key rotation, backup, and recovery are manual procedures (no automation). Production: Vault automates these. |
| A stolen live session (8h token) | Short-lived token (8h prototype, 15min production). Step-up MFA blocks sensitive actions. | 8h window is long for a stolen token that can still read documents. Production: 15-min access + httpOnly refresh cookie + rotation. |
| Backup media | Data directory structure documented. Backup procedures noted in SECURITY.md Key lifecycle. | No automated backup, no backup encryption verification. Production: encrypted backup + restore tests. |
| A privileged account rewriting the whole audit chain | REVOKE UPDATE/DELETE closes the app-user path. Chain integrity verified by `/audit/verify` with `first_break_at`. | A `postgres` superuser can rewrite the chain without detection. Mitigate in production: OS-level audit of superuser DB access; immutable audit export to a separate write-once store. |

---

## Out of Scope

These threats are explicitly not addressed by PRAMAAN. Judges should not expect defences here.

| Threat | Why out of scope |
|--------|-----------------|
| Full root / OS compromise of any server | Physical/kernel security is an infrastructure concern, not an application concern. All application-layer controls are bypassable at root. |
| Physical access to hardware | Out of scope. Requires physical security controls (locked rooms, tamper-evident hardware). |
| A compromised cryptographic library (`cryptography` package) | Assumed-trusted dependency. Supply-chain security is a separate programme. |
| Formal verification of cryptographic properties | Prototype timeline and team size preclude formal methods. Standard algorithms (AES-256-GCM, HKDF, Ed25519, SHA-256) are used as specified. |
| Production disaster recovery and high availability | DR/HA is deferred to production infrastructure (MinIO replication, Postgres streaming replication, multi-AZ). |
| Certified PKI / legal e-signature deployment | Ed25519 signatures prove cryptographic authorship; legal admissibility of digital signatures for court proceedings requires certified PKI frameworks, which are out of scope. |
| Network-level attacks (DDoS, BGP hijack, etc.) | Infrastructure-level; not addressed at the application layer. |

---

*Last updated to match slide 4 of `ppts/SIH2026_PS26190_leet_Idea_Submission_v1.pptx`.
When the slide changes, update this file in the same commit.*
