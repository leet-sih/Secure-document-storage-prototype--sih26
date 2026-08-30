"""
test_ocr.py — OCR extraction and status mapping (no DB needed).

These validate app.core.ocr directly, in the style of test_crypto.py: pure unit
tests, no Flask app fixture, no Postgres. Pages are rendered at test time, so no
sample document is committed to the repo and the tests run anywhere.

Skips cleanly when the tesseract binary is not installed, so a developer without
it does not see red for a system package they may not need.

Source: feature_plans/ocr_plan.md
"""

import io

import pytest

from app.core import ocr

PIL = pytest.importorskip("PIL", reason="Pillow not installed")
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

needs_tesseract = pytest.mark.skipif(
    not ocr.engine_available(), reason="tesseract binary not installed"
)

LINES = [
    "FIRST INFORMATION REPORT",
    "Station: Central District",
    "Registered on 12 March 2026",
    "Complainant statement attached",
]


def _font(size=30):
    for path in (
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _page_image(lines=None, size=(1000, 380)):
    img = Image.new("L", size, color=255)
    draw = ImageDraw.Draw(img)
    font = _font()
    for i, line in enumerate(lines or LINES):
        draw.text((50, 40 + i * 70), line, fill=0, font=font)
    return img


def _png_bytes(**kw) -> bytes:
    buf = io.BytesIO()
    _page_image(**kw).save(buf, format="PNG", dpi=(200, 200))
    return buf.getvalue()


def _scanned_pdf_bytes() -> bytes:
    """A PDF with no text layer — an image pasted onto a page, i.e. a scan."""
    buf = io.BytesIO()
    _page_image().convert("RGB").save(buf, format="PDF", resolution=150)
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────
# Which documents need OCR
# ──────────────────────────────────────────────────────────────────

def test_images_always_need_ocr():
    for mime in ("image/jpeg", "image/png", "image/tiff"):
        assert ocr.needs_ocr(mime) is True


def test_non_image_types_never_need_ocr():
    """DOCX/XLSX/plain text carry their own text; OCR would be wrong and slow."""
    for mime in ("text/plain", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
        assert ocr.needs_ocr(mime) is False


def test_a_scanned_pdf_needs_ocr():
    assert ocr.pdf_has_text_layer(_scanned_pdf_bytes()) is False
    assert ocr.needs_ocr("application/pdf", _scanned_pdf_bytes()) is True


def test_a_digital_pdf_does_not_need_ocr():
    """A born-digital PDF already has text; OCR would be slower and worse."""
    pytest.importorskip("reportlab", reason="reportlab not installed")
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for i, line in enumerate(LINES):
        c.drawString(72, 700 - i * 24, line)
    c.save()
    data = buf.getvalue()

    assert ocr.pdf_has_text_layer(data) is True
    assert ocr.needs_ocr("application/pdf", data) is False
    assert "FIRST INFORMATION REPORT" in ocr.extract_pdf_text_layer(data)


def test_a_corrupt_pdf_is_not_mistaken_for_a_digital_one():
    """Garbage must fall through to OCR (which will fail loudly), not be
    silently treated as a document that already has its text."""
    assert ocr.pdf_has_text_layer(b"%PDF-1.4 truncated") is False


# ──────────────────────────────────────────────────────────────────
# Extraction
# ──────────────────────────────────────────────────────────────────

@needs_tesseract
def test_extract_reads_a_scanned_image():
    result = ocr.extract(_png_bytes(), "fir.png")
    assert result.status in (ocr.DONE, ocr.LOW_CONFIDENCE)
    text = result.text.lower()
    for word in ("information", "report", "station", "march"):
        assert word in text, f"missing {word!r} in {result.text!r}"
    assert result.page_count == 1
    assert 0.0 <= result.confidence <= 1.0


@needs_tesseract
def test_extract_reads_a_scanned_pdf():
    result = ocr.extract(_scanned_pdf_bytes(), "fir.pdf")
    assert result.status in (ocr.DONE, ocr.LOW_CONFIDENCE)
    assert "report" in result.text.lower()
    assert result.page_count == 1


@needs_tesseract
def test_extracted_text_is_safe_for_postgres():
    """Control characters break the text column and the FTS trigger."""
    result = ocr.extract(_png_bytes(), "fir.png")
    assert "\x00" not in result.text
    assert not any(ord(c) < 9 for c in result.text)
    assert "\n\n\n" not in result.text


@needs_tesseract
def test_extract_never_raises_on_rubbish_input():
    """OCR is best-effort and must never be able to fail an upload."""
    for data, name in [
        (b"", "empty.png"),
        (b"not an image at all", "junk.png"),
        (b"%PDF-1.4 truncated", "junk.pdf"),
        (_png_bytes(), "noextension"),
    ]:
        result = ocr.extract(data, name)
        assert result.status == ocr.FAILED
        assert result.detail, "a failure should say why"


def test_missing_tesseract_reports_a_deployment_problem(monkeypatch):
    """Not a bad document. The message must not blame the file."""
    monkeypatch.setattr(ocr, "engine_available", lambda: False)
    result = ocr.extract(b"whatever", "fir.png")
    assert result.status == ocr.FAILED
    assert "tesseract" in result.detail.lower()


# ──────────────────────────────────────────────────────────────────
# Status mapping (thresholds from the plan)
# ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "confidence,expected",
    [
        (1.00, ocr.DONE), (0.92, ocr.DONE), (0.80, ocr.DONE),
        (0.799, ocr.LOW_CONFIDENCE), (0.72, ocr.LOW_CONFIDENCE), (0.60, ocr.LOW_CONFIDENCE),
        (0.599, ocr.FAILED), (0.30, ocr.FAILED), (0.0, ocr.FAILED),
    ],
)
def test_confidence_maps_to_the_documented_status(confidence, expected):
    assert ocr._status_for(confidence) == expected


def test_score_confidence_weights_by_text_length():
    """An unweighted mean lets one noise character sink a clean page — and that
    decides whether a human is asked to retype the document."""
    class R:
        def __init__(self, text, confidence):
            self.text = text
            self.confidence = confidence

    regions = [R("a long confident line of real text", 0.95), R("|", 0.10)]
    assert ocr.score_confidence(regions) > 0.85
    assert ocr.score_confidence([]) == 0.0


# ──────────────────────────────────────────────────────────────────
# The security line
# ──────────────────────────────────────────────────────────────────

@needs_tesseract
def test_ocr_never_writes_the_plaintext_to_disk(tmp_path, monkeypatch):
    """The claim the whole feature rests on, asserted rather than commented.

    A decrypted document written to a temp file would survive in the filesystem,
    in backups and in crash dumps — undoing encryption at rest.
    """
    import tempfile

    watched = tmp_path / "watch"
    watched.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(watched))
    monkeypatch.chdir(watched)

    before = set(watched.rglob("*"))
    ocr.extract(_png_bytes(), "fir.png")
    assert set(watched.rglob("*")) == before, "OCR wrote the plaintext to disk"


def test_the_engine_cannot_reach_the_network():
    """Offline is enforced at import, not by policy."""
    import os

    import app.core.ocr_engine.config  # noqa: F401  (import sets the flags)

    assert os.environ.get("HF_HUB_OFFLINE") == "1"
    assert os.environ.get("TRANSFORMERS_OFFLINE") == "1"


def test_handwriting_is_optional():
    """The prototype must run with only the tesseract binary installed."""
    from app.core.ocr_engine.engines import get_engine

    assert get_engine("trocr").is_available() in (True, False)  # never raises


# ──────────────────────────────────────────────────────────────────
# Language packs
# ──────────────────────────────────────────────────────────────────

def test_missing_language_packs_do_not_fail_every_document(monkeypatch):
    """The default is eng+hin, and the Indic packs are a Dockerfile change.

    Tesseract does not degrade — "eng+hin" without tesseract-ocr-hin fails the
    whole call — so an un-updated image would return FAILED for every single
    upload while looking correctly configured.
    """
    monkeypatch.setattr(ocr, "available_languages", lambda: {"eng", "osd"})
    assert ocr.resolve_language("eng+hin") == "eng"
    assert ocr.resolve_language("eng+hin+tam") == "eng"


def test_installed_packs_are_kept(monkeypatch):
    monkeypatch.setattr(ocr, "available_languages", lambda: {"eng", "hin", "tam"})
    assert ocr.resolve_language("eng+hin") == "eng+hin"
    assert ocr.resolve_language("eng+hin+ben") == "eng+hin"


def test_language_falls_back_even_with_no_english(monkeypatch):
    monkeypatch.setattr(ocr, "available_languages", lambda: {"hin"})
    assert ocr.resolve_language("tam") == "hin"


def test_unknown_language_list_is_left_alone(monkeypatch):
    """If we cannot tell what is installed, do not second-guess the operator."""
    monkeypatch.setattr(ocr, "available_languages", lambda: set())
    assert ocr.resolve_language("eng+hin") == "eng+hin"


@needs_tesseract
def test_result_records_the_language_actually_used():
    """ocr_language must not claim a pack that was never loaded."""
    result = ocr.extract(_png_bytes(), "fir.png", language="eng+hin")
    assert result.language == ocr.resolve_language("eng+hin")
    for part in result.language.split("+"):
        assert part in ocr.available_languages()
