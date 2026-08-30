# OCR integration

Implements `feature_plans/ocr_plan.md`. **No existing file was modified** — everything
below is new. That leaves exactly one thing for you to do, in step 3.

## What was added

| File | What it is |
|---|---|
| `app/core/ocr.py` | The adapter. The only file that knows about Flask, SQLAlchemy or `Document`. |
| `app/core/ocr_engine/` | Vendored OCR engine (7 modules). Pure computation, no framework. |
| `tests/test_ocr.py` | 28 unit tests, no DB, in the style of `test_crypto.py`. |
| `requirements-ocr.txt` | OCR dependencies, kept out of `requirements.txt`. |

The public API is exactly the one the plan names: `run_ocr_inline()`, `needs_ocr()`,
`preprocess_image()`, `run_tesseract()`, `score_confidence()`.

## Setup

**1. Install the tesseract binary** (a system package, not pip):

```bash
brew install tesseract tesseract-lang          # macOS dev
# Debian/Ubuntu, add to the Dockerfile:
#   apt-get install -y tesseract-ocr tesseract-ocr-hin tesseract-ocr-tam \
#       tesseract-ocr-tel tesseract-ocr-ben tesseract-ocr-guj \
#       libglib2.0-0 libsm6 libxrender1 libxext6
```

**2. Install the Python dependencies:**

```bash
pip install -r requirements-ocr.txt
```

**3. Uncomment the hook** at the end of `upload_document()` in
`app/services/document_service.py` — it is already written there as a comment:

```python
try:
    from app.core import ocr
    ocr.run_ocr_inline(doc)
except Exception:
    current_app.logger.exception("OCR failed for document %s", doc.id)
```

That is the whole wiring. `search_text` is populated, and the existing FTS trigger fires.

**Verify:** `pytest tests/test_ocr.py -q` → 27 passed, 1 skipped (more skip without
tesseract or reportlab).

## It degrades instead of breaking

Every one of these leaves the document **ACTIVE and fully encrypted**, changing only
`ocr_status`:

| Situation | Result |
|---|---|
| tesseract not installed | `FAILED`, detail says it is a server problem, not a bad file |
| Hindi/Tamil packs missing | falls back to the packs that ARE installed, logs a warning |
| corrupt or empty file | `FAILED` with a reason |
| > 50 pages | `FAILED` (the plan's cap) |
| non-image, non-PDF | `NOT_APPLICABLE` |
| born-digital PDF | text layer read directly, `NOT_APPLICABLE` |

The missing-language-pack case is worth knowing about. The default is `eng+hin`, and
tesseract does **not** degrade — asking for `eng+hin` without `tesseract-ocr-hin` fails
the entire call. Without the fallback, an image whose Dockerfile had not been updated
would return `FAILED` for *every* document while looking correctly configured.
`ocr_language` records the language that actually ran, never the one that was requested.

## The security line

OCR reconstructs the document **in memory** via `document_service.reconstruct_bytes()`,
reads it, and writes only derived text to the database. **No decrypted file is ever
written to disk** — not even a temp file. `test_ocr_never_writes_the_plaintext_to_disk`
asserts this by watching the filesystem during a run, rather than leaving it as a comment
that could quietly stop being true.

The engine sets `HF_HUB_OFFLINE` / `TRANSFORMERS_OFFLINE` at import, so no OCR component
can reach the network even if a model library wants to.

## Deviations from the plan, and why

**`pypdfium2` instead of `pdf2image` + `PyMuPDF`.** It bundles its own renderer, so
`poppler-utils` is no longer a system dependency, and it reads PDFs **straight from
bytes** — which is what makes the no-temp-file guarantee possible. `pdf2image` shells out
to poppler with file paths. It also does the text-layer check, so PyMuPDF is unnecessary.

**Born-digital PDFs get their text layer extracted.** The plan's `needs_ocr()` correctly
returns `False` for them, but nothing else populates `search_text`, so a perfectly
readable PDF would have been silently unsearchable. It is ~10 lines using a dependency
already present. Delete `extract_pdf_text_layer` and its call in `run_ocr_inline` if you
would rather keep OCR strictly to scans.

**Handwriting support is included but off.** The plan names handwritten FIRs as a core
input, and Tesseract is weak on handwriting. The engine can route low-confidence lines to
TrOCR instead — but only if its weights are on disk, and it is **not** enabled here.
At 1–3 s per handwritten *line* on CPU it is far too slow for the inline upload path.
Treat it as available for a GPU deployment, or once OCR moves off the request. Everything
works typed-only without it.

## What this does not do

- **No migration.** The `ocr_*` columns already exist on the `Document` model; if your
  database predates them, generate the migration.
- **No API endpoint.** `PATCH /documents/{id}/ocr-text` (plan step 6) is not implemented —
  it belongs in the documents blueprint, which is an existing file.
- **No frontend.** The status badge and correction textarea (plan step 7) are not built.
- **No Dockerfile change.** The tesseract packages need adding there; the command is above.

## One caveat about confidence

`ocr_confidence` is how sure the recogniser was, **not how correct it was**. OCR is
routinely confident and wrong — `0x8fa21c` reads as `Ox8fa21c` at around 0.9, which no
threshold will catch. A `DONE` status means "no review flagged", not "verified". This is
why the plan's manual-correction path matters for more than just `LOW_CONFIDENCE`, and
identifiers are worth a second look regardless of score.
