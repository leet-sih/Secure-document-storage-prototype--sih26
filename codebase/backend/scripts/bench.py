#!/usr/bin/env python3
"""
bench.py — upload/download/tamper benchmarks for PRAMAAN.

PURPOSE:
    Measures real prototype performance figures and writes them to docs/BENCHMARKS.md.
    The deck (slide 5) promises figures "reported from the prototype, not claimed now."
    Only publish numbers you actually measured on the demo machine.

MEASURES:
    Upload   — wall time, encryption time, peak RSS, storage overhead (10/100/500 MB)
    Download — auth check, integrity verify, decrypt, total wall time (same sizes)
    Tamper   — detection time, bytes served after failure (MUST be 0)
    Concurrency — 1/5/10 users at 10 MB (only publish what you actually ran)

IMPORTANT — 500 MB note:
    The pre-verify pass buffers the whole document in RAM. If peak RSS exceeds available
    memory on the demo machine, report it honestly in BENCHMARKS.md and reduce the cap.
    Do NOT quietly drop the row or fake the number.

USAGE:
    python backend/scripts/bench.py [--output docs/BENCHMARKS.md]

TODO: implement each benchmark function below.
"""

import argparse
import time

# TODO: imports (requests or flask test client, resource/tracemalloc, threading)

SIZES_MB = [10, 100, 500]


def bench_upload(size_mb: int) -> dict:
    """Upload a synthetic file of size_mb MB. Return timing + memory metrics. TODO."""
    raise NotImplementedError


def bench_download(doc_id: str, size_mb: int) -> dict:
    """Download doc_id. Return auth_ms, verify_s, decrypt_s, total_s. TODO."""
    raise NotImplementedError


def bench_tamper(doc_id: str) -> dict:
    """Corrupt one chunk; measure detection time; assert bytes_served == 0. TODO."""
    raise NotImplementedError


def bench_concurrency(n_users: int, size_mb: int = 10) -> dict:
    """Run n_users concurrent uploads of size_mb MB. Return avg wall time. TODO."""
    raise NotImplementedError


def write_benchmarks_md(results: dict, output_path: str) -> None:
    """Render results into docs/BENCHMARKS.md format. TODO."""
    raise NotImplementedError


def main() -> None:
    parser = argparse.ArgumentParser(description="PRAMAAN benchmark suite")
    parser.add_argument("--output", default="docs/BENCHMARKS.md")
    args = parser.parse_args()

    results: dict = {
        "upload": {},
        "download": {},
        "tamper": {},
        "concurrency": {},
    }

    print("Running upload benchmarks...")
    for mb in SIZES_MB:
        results["upload"][mb] = bench_upload(mb)
        print(f"  {mb} MB: {results['upload'][mb]}")

    print("Running download benchmarks...")
    for mb in SIZES_MB:
        # TODO: use doc_ids from the upload run above
        results["download"][mb] = bench_download(doc_id="TODO", size_mb=mb)
        print(f"  {mb} MB: {results['download'][mb]}")

    print("Running tamper benchmark...")
    results["tamper"] = bench_tamper(doc_id="TODO")
    assert results["tamper"]["bytes_served"] == 0, "CRITICAL: tampered doc served bytes!"
    print(f"  {results['tamper']}")

    print("Running concurrency benchmarks...")
    for n in [1, 5, 10]:
        results["concurrency"][n] = bench_concurrency(n_users=n)
        print(f"  {n} users: {results['concurrency'][n]}")

    write_benchmarks_md(results, args.output)
    print(f"\nBenchmarks written to {args.output}")


if __name__ == "__main__":
    main()
