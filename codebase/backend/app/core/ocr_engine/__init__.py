"""Vendored OCR engine. Do not call this package directly — use `app.core.ocr`.

WHERE THIS CAME FROM
    An external OCR service, vendored here rather than pip-installed so the
    prototype stays `pip install -r requirements.txt` with no private index and
    no submodule. Treat these files as a third-party library: fix bugs upstream
    and re-vendor, rather than editing in place, or the next update overwrites
    the fix.

    Excluded from the vendored copy: the CLI, and the searchable-PDF writer
    (which would add reportlab for output this system has nowhere to store).

WHAT IT DOES
    Two-path OCR behind one interface. Tesseract reads the page and supplies
    layout in a single pass; lines it reads poorly go to a printed/handwritten
    classifier, and handwritten ones are re-read by TrOCR. That matters here
    because handwritten FIRs are a stated input for this system and Tesseract
    alone is weak on handwriting.

    TrOCR is OPTIONAL. Without its weights on disk the pipeline runs typed-only
    and flags handwritten lines as low-confidence rather than failing — so the
    prototype works with nothing but the tesseract binary installed.

OFFLINE BY CONSTRUCTION
    `config.py` sets HF_HUB_OFFLINE / TRANSFORMERS_OFFLINE at import time, so
    nothing in this package can reach the network at runtime even if a model
    library wants to. That is deliberate and matches this system's requirement
    that document contents never leave the server. Do not remove it.

LAYERING
    Pure computation: no Flask, no SQLAlchemy, no request context, no knowledge
    of this application's models. `app/core/ocr.py` is the only adapter between
    it and the rest of the app.
"""

__version__ = "0.1.0"
