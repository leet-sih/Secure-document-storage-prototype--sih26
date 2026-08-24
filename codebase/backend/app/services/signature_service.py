"""
signature_service.py — Ed25519 document signatures.

sign_document(document_id, signer) -> DocumentSignature
    Loads/creates signer keypair (private -> KMS, public -> User.signing_public_key),
    builds payload = SHA256(integrity_hash | doc_id | signer_id | ts), signs, stores.
    409 if signer already signed this document.
verify_signatures(document_id) -> list[dict]
    For each signature: verify Ed25519 AND check current integrity_hash still equals
    integrity_hash_at_signing. Updates is_valid/last_verified_at.
revoke_signature(document_id, signature_id, actor) -> None
    Only the signer or SUPER_ADMIN. Sets revoked_at + is_valid=False (row kept for audit).

STORES: rows in document_signatures; public key in users.signing_public_key.
Full design: ../../feature_plans/digital_signatures_plan.md
"""


def sign_document(document_id: str, signer):
    raise NotImplementedError


def verify_signatures(document_id: str) -> list[dict]:
    raise NotImplementedError


def revoke_signature(document_id: str, signature_id: str, actor) -> None:
    raise NotImplementedError
