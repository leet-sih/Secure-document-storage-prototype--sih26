"""
schemas/ — marshmallow schemas for request validation and response serialization.

RULES:
    - Every request body is validated with a schema `.load()` — never read request.json raw.
    - Set Meta.unknown = RAISE so clients can't smuggle extra fields (e.g. `role`).
    - Mark secrets load_only; mark server-generated fields dump_only.
    - NEVER dump: password_hash, totp_secret, master keys, chunk IVs/hashes,
      signature internals, prev_hash/this_hash.

One file per domain: auth, user, case, document, audit, signature, sharing, search.
"""
