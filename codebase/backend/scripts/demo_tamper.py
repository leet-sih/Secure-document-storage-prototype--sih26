#!/usr/bin/env python3
"""
demo_tamper.py — automated five-step tamper demonstration for PRAMAAN.

PURPOSE:
    Proves that a corrupted chunk is detected and that ZERO bytes of the tampered
    document are ever served to the client. This is the central claim of the deck.

STEPS (must all succeed for the demo to pass):
    1. Upload a known file to a known case         → print doc_id, chunk count, integrity_hash
    2. Download it, checksum it                    → assert byte-identical to the original
    3. Corrupt one chunk object on Server B        → print which chunk and the byte changed
    4. Attempt download again                      → assert HTTP 422, assert 0 bytes received
    5. Read the audit trail                        → assert INTEGRITY_VIOLATION event exists

Step 4's "0 bytes received" assertion is the single most important check in this repo.
It proves that no partial/tampered content was streamed to the client before the abort.

USAGE:
    Set up .env and run:
        python backend/scripts/demo_tamper.py

TODO: implement each step below. The test counterpart lives in:
    backend/tests/test_download_tamper.py
"""

import sys

# TODO: imports (requests or flask test client, hashlib, os, struct)


def step1_upload(case_id: str, file_path: str) -> dict:
    """Upload file_path to case_id. Return { doc_id, chunk_count, integrity_hash }. TODO."""
    raise NotImplementedError


def step2_download_and_verify(doc_id: str, original_path: str) -> None:
    """Download doc_id and assert byte-identical to original_path. TODO."""
    raise NotImplementedError


def step3_corrupt_chunk(doc_id: str) -> dict:
    """Find one chunk object for doc_id on Server B; flip one byte.
    Return { storage_key, byte_offset, original_byte, new_byte }. TODO."""
    raise NotImplementedError


def step4_download_must_fail(doc_id: str) -> None:
    """Attempt download; assert HTTP 422 and assert 0 bytes in response body. TODO."""
    raise NotImplementedError


def step5_verify_audit_event(doc_id: str) -> None:
    """Query /audit and assert INTEGRITY_VIOLATION event exists for doc_id. TODO."""
    raise NotImplementedError


def main() -> None:
    print("=" * 60)
    print("PRAMAAN — Tamper Demo")
    print("=" * 60)

    # TODO: configure case_id and test file path from CLI args or env
    case_id = "TODO"
    test_file = "TODO"

    print("\nStep 1: Uploading known file...")
    result = step1_upload(case_id, test_file)
    print(f"  doc_id:         {result['doc_id']}")
    print(f"  chunk_count:    {result['chunk_count']}")
    print(f"  integrity_hash: {result['integrity_hash']}")

    print("\nStep 2: Downloading — must be byte-identical...")
    step2_download_and_verify(result['doc_id'], test_file)
    print("  PASS: download is byte-identical to original")

    print("\nStep 3: Corrupting one chunk on Server B...")
    corruption = step3_corrupt_chunk(result['doc_id'])
    print(f"  storage_key:  {corruption['storage_key']}")
    print(f"  byte_offset:  {corruption['byte_offset']}")
    print(f"  original:     0x{corruption['original_byte']:02x}")
    print(f"  new:          0x{corruption['new_byte']:02x}")

    print("\nStep 4: Attempting download of tampered document...")
    step4_download_must_fail(result['doc_id'])
    print("  PASS: HTTP 422 received, 0 bytes served")

    print("\nStep 5: Checking audit trail for INTEGRITY_VIOLATION...")
    step5_verify_audit_event(result['doc_id'])
    print("  PASS: INTEGRITY_VIOLATION event found in audit log")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE — All 5 steps passed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
