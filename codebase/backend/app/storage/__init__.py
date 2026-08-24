"""
storage/ — where encrypted chunks physically live.

    chunk_store.py — PROTOTYPE: local filesystem store (put/get/delete ciphertext chunks).
                     Swapped for MinIO/S3 in production with the same function signatures.

Only document_service talks to this. Objects stored here are ALWAYS ciphertext.
"""
