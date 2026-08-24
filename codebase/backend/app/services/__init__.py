"""
services/ — business logic. Blueprints stay thin and call these.

    auth_service       credential verification, token issuance, MFA
    user_service       user CRUD, first-login, password change, deactivation
    case_service       case CRUD + the case-scoped access checks (404 for non-members)
    document_service   the chunked upload/download pipeline (crypto + MinIO + KMS)
    audit_service      hash-chained audit recorder + chain verification
    signature_service  Ed25519 sign / verify / revoke
    sharing_service    share-link create / access / revoke
    search_service     metadata + full-text search, scoped to accessible cases

RULE: audit_service.record(...) is called from the BLUEPRINT layer after an action, not
buried in services — keep audit calls explicit and visible. (Exception: security events
like UNAUTHORIZED_ACCESS_ATTEMPT recorded inside guards.)
"""
