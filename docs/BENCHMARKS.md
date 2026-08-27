# Benchmarks — PRAMAAN: Secure Evidence Vault

> **Status:** NOT YET MEASURED. This file is a template.
> Run `backend/scripts/bench.py` to populate with real numbers.
> The deck (slide 5) promises "figures reported from the prototype, not claimed now."
> Do not publish any number you did not actually measure.

---

## Test Environment

| Field | Value |
|-------|-------|
| Date | TODO |
| Hardware | TODO (CPU, RAM, disk type) |
| OS | TODO |
| Python version | TODO |
| CHUNK_STORE_BACKEND | TODO (local / sftp) |
| Network (for sftp) | TODO |

---

## Upload Benchmarks

| File size | Wall time (s) | Encryption time (s) | Peak RSS (MB) | Storage overhead vs plaintext |
|-----------|--------------|--------------------|--------------|-----------------------------|
| 10 MB | TODO | TODO | TODO | TODO |
| 100 MB | TODO | TODO | TODO | TODO |
| 500 MB | TODO | TODO | TODO | TODO |

> Note: 500 MB pre-verify pass buffers the whole document in RAM. If peak RSS exceeds available
> memory on the demo machine, report this here and align the upload cap to 100 MB (and update
> the deck accordingly). Do NOT publish a 500 MB benchmark you did not run.

---

## Download / Retrieval Benchmarks

| File size | Auth check (ms) | Integrity verify (s) | Decrypt (s) | Total wall time (s) |
|-----------|----------------|---------------------|-------------|---------------------|
| 10 MB | TODO | TODO | TODO | TODO |
| 100 MB | TODO | TODO | TODO | TODO |
| 500 MB | TODO | TODO | TODO | TODO |

---

## Tamper Detection Benchmarks

| Scenario | Detection time (ms) | Bytes served after failure |
|----------|--------------------|-----------------------------|
| 1 corrupt chunk (10 MB doc) | TODO | **must be 0** |
| 1 corrupt chunk (100 MB doc) | TODO | **must be 0** |

> The "bytes served = 0" assertion is non-negotiable. If this row shows anything other than 0,
> the prototype has a critical bug. See `backend/tests/test_download_tamper.py`.

---

## Concurrency Benchmarks

> Only publish numbers you actually tested. Do not extrapolate.

| Concurrent users | Upload 10 MB (avg wall time) | Download 10 MB (avg wall time) |
|-----------------|------------------------------|-------------------------------|
| 1 | TODO | TODO |
| 5 | TODO | TODO |
| 10 | TODO | TODO |

---

*Populated by `backend/scripts/bench.py`. Run: `python backend/scripts/bench.py` from repo root.*
