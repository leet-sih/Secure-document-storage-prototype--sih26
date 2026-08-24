# Feature Plans — Contents

| File | Feature | Scope |
|------|---------|-------|
| `auth_plan.md` | Authentication & MFA | Full login flow, TOTP, JWT refresh, rate limiting, account lockout |
| `user_management_plan.md` | User Management | No self-registration, role system, first-login flow, password policy |
| `case_management_plan.md` | Case Management | Case lifecycle (OPEN→ARCHIVED), case-scoped access control, member management |
| `chunked_document_storage_plan.md` | Chunked Encryption ★ | HKDF key derivation, per-chunk AES-256-GCM, upload/download flows with exact pseudocode, tamper detection |
| `audit_trail_plan.md` | Audit Trail | Hash-chain design, all 30+ event types, concurrent write safety, chain verification |
| `search_plan.md` | Search & Retrieval | Metadata filters, PostgreSQL FTS with tsvector, tag system, relevance scoring |
| `digital_signatures_plan.md` | Digital Signatures | Ed25519 key pairs, what gets signed, post-signing tamper detection, legal validity note |
| `document_sharing_plan.md` | Secure Sharing | Token hashing, email gate, atomic max-uses counter, 48h expiry |
| `ocr_plan.md` | OCR (Roadmap) | Tesseract + OpenCV pre-processing, confidence thresholds, Indian language support |
| `secure_playground_plan.md` | AI Playground (Roadmap) | Ollama + Mistral 7B, ephemeral Redis sessions, prompt injection prevention |
| `ai_retrieval_plan.md` | AI Retrieval (Roadmap) | Qdrant vector DB, hybrid BM25+cosine re-ranking, access-controlled vector search |
