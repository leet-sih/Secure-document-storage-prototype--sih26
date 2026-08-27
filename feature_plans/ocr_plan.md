# Feature Plan: OCR-Based Document Digitisation

> **Status:** PROTOTYPE SCOPE — Day 6 (Aug 29). Implement for Sep 2. See docs/TODO.md Phase 5.
>
> **Execution model — NO Celery:** Run OCR inline on the upload request, after chunks are stored
> and the document record is committed. For the prototype (1–2 page scans typical in demo),
> inline is fast enough and simplest to demo. Hard page cap: refuse OCR for docs > 50 pages;
> set ocr_status=FAILED and log the reason. This keeps the upload response time predictable.
>
> **Language packs:** The deck names five Indic scripts — install all five or change the slide:
> Hindi (Devanagari), Tamil, Telugu, Bengali, Gujarati. See Dockerfile section below.
>
> **Security line:** OCR reconstructs the document in memory on the app server, writes only
> derived text (search_text) to the database, and NEVER persists a decrypted file to disk.
> This is the answer a judge will ask for — keep it in the code comment too.

---

## What Is This Feature?

Law enforcement agencies receive enormous volumes of paper documents: handwritten FIRs, typewritten statements, physical court orders. OCR (Optical Character Recognition) converts scanned images and photographs of these documents into searchable digital text.

The OCR pipeline:
1. Accepts scanned images or PDFs (uploaded just like any other document)
2. Detects that the file is a scan (image-only PDF or raw image)
3. Pre-processes the image (deskew, denoise, binarize)
4. Runs Tesseract OCR to extract text
5. Stores extracted text in `documents.search_text` (existing column)
6. Makes the document fully searchable without any user effort

---

## Why Tesseract?

Tesseract is open-source (Apache 2.0), battle-tested, runs 100% on-premise (critical for law enforcement data), supports Hindi and other regional Indian scripts (Devanagari, Telugu, Tamil, etc.) with `tessdata` language packs, and has a Python binding (`pytesseract`). No data leaves the server.

Alternative: Azure Form Recognizer / Google Document AI — cloud-based, higher accuracy, but data leaves the government network. Unacceptable for this system.

---

## Architecture

```
Upload endpoint receives file.pdf (scanned)
         │
         ▼
Celery task: process_ocr_task(document_id)
         │
         ├── Step 1: Pre-processing (OpenCV)
         │     ├── Convert PDF pages to images (pdf2image / PyMuPDF)
         │     ├── Grayscale conversion
         │     ├── Adaptive thresholding (binarize)
         │     ├── Deskew (detect and correct rotation up to ±15°)
         │     └── Denoise (Gaussian blur + morphological operations)
         │
         ├── Step 2: OCR (Tesseract)
         │     ├── Run tesseract on each page image
         │     ├── Language: eng+hin (English + Hindi)
         │     ├── PSM 3 (automatic page segmentation)
         │     └── OEM 3 (LSTM neural net engine)
         │
         ├── Step 3: Post-processing
         │     ├── Concatenate page texts
         │     ├── Compute confidence score (average word confidence)
         │     ├── Flag low-confidence extractions (< 60%) for manual review
         │     └── Clean: remove control characters, normalize whitespace
         │
         └── Step 4: Store
               ├── Update documents.search_text = extracted_text
               ├── Update documents.ocr_confidence = avg_confidence
               ├── Update documents.ocr_status = "DONE" | "LOW_CONFIDENCE" | "FAILED"
               └── Trigger FTS index update (search_vector trigger fires automatically)
```

---

## Database Changes

```sql
ALTER TABLE documents ADD COLUMN ocr_status TEXT DEFAULT 'NOT_APPLICABLE';
-- Values: NOT_APPLICABLE (non-image), PENDING, IN_PROGRESS, DONE, LOW_CONFIDENCE, FAILED

ALTER TABLE documents ADD COLUMN ocr_confidence FLOAT;
-- 0.0 to 1.0 — average Tesseract word confidence

ALTER TABLE documents ADD COLUMN ocr_language TEXT DEFAULT 'eng+hin';
-- Language pack used

ALTER TABLE documents ADD COLUMN ocr_page_count INT;
-- Number of pages processed

CONSTRAINT chk_ocr_status CHECK (ocr_status IN (
    'NOT_APPLICABLE', 'PENDING', 'IN_PROGRESS', 'DONE', 'LOW_CONFIDENCE', 'FAILED'
));
```

---

## Determining If OCR Is Needed

```python
def needs_ocr(mime_type: str, document_id: str) -> bool:
    # Direct image files always need OCR
    if mime_type in {'image/jpeg', 'image/png', 'image/tiff'}:
        return True

    # For PDFs: check if the PDF contains selectable text
    # A PDF with no text layer is a scanned document
    if mime_type == 'application/pdf':
        return not pdf_has_text_layer(document_id)

    # DOCX, XLSX — text extractable directly
    return False

def pdf_has_text_layer(document_id: str) -> bool:
    # Download and reconstruct document (or just first chunk for speed)
    # Use PyMuPDF: if page.get_text() returns > 50 chars, it has a text layer
    ...
```

---

## Pre-Processing Details

Skipped scans are a major source of OCR failure. Pre-processing steps:

```python
import cv2
import numpy as np

def preprocess_image(image: np.ndarray) -> np.ndarray:
    # 1. Grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 2. Deskew — detect rotation angle via Hough lines or projection profile
    angle = detect_skew_angle(gray)
    if abs(angle) > 0.5:  # only rotate if skew > 0.5°
        gray = rotate_image(gray, angle)

    # 3. Denoise
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # 4. Adaptive thresholding (handles uneven lighting / shadows on paper)
    binary = cv2.adaptiveThreshold(
        denoised, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        11, 2
    )

    # 5. Morphological dilation (thickens thin strokes — helps Tesseract)
    kernel = np.ones((1, 1), np.uint8)
    processed = cv2.dilate(binary, kernel, iterations=1)

    return processed
```

---

## Language Support

India-specific language packs for Tesseract:

```
tessdata languages:
  eng     - English
  hin     - Hindi (Devanagari script)
  tam     - Tamil
  tel     - Telugu
  kan     - Kannada
  mal     - Malayalam
  ben     - Bengali
  guj     - Gujarati
  mar     - Marathi
  pan     - Punjabi (Gurmukhi)
  urd     - Urdu (Arabic script)
```

At upload time, the user can specify the expected language. Default: `eng+hin`.

---

## Confidence Thresholds

| Confidence | Status | Action |
|-----------|--------|--------|
| ≥ 80% | DONE | Fully searchable; no review needed |
| 60–79% | LOW_CONFIDENCE | Searchable but flagged; UI shows warning |
| < 60% | FAILED | Not searchable; UI shows "Manual transcription required" |

A CASE_OFFICER with LOW_CONFIDENCE documents can manually correct the extracted text via a simple text editor in the UI. Corrections are stored in `search_text` and re-indexed.

---

## UI (Prototype)

Show OCR status on the document detail view using the ocr_status value:

```
DONE           →  ✓ Text extracted (confidence: 92%)
LOW_CONFIDENCE →  ⚠ Extracted with low confidence (72%) — review recommended
FAILED         →  ✗ OCR failed — manual transcription required
NOT_APPLICABLE →  (no badge — plaintext document)
PENDING        →  ⏳ Processing…
```

A CASE_OFFICER with LOW_CONFIDENCE documents can manually correct the extracted text via a
plain textarea in the UI. Corrections update search_text and re-trigger the FTS index.

---

## Dependencies

```
pytesseract==0.3.*
Pillow==10.*
pdf2image==1.17.*          # requires poppler
PyMuPDF==1.24.*            # faster PDF text extraction
opencv-python-headless==4.10.*
numpy==1.26.*
```

System packages (Docker) — all five Indic packs from the deck:
```dockerfile
RUN apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-hin \
    tesseract-ocr-tam \
    tesseract-ocr-tel \
    tesseract-ocr-ben \
    tesseract-ocr-guj \
    poppler-utils \
    libglib2.0-0 libsm6 libxrender1 libxext6
```

---

## Inline Execution (Prototype — no Celery)

Called from `document_service.py` after upload completes, before returning the HTTP response:

```python
def run_ocr_inline(document: Document) -> None:
    """Run OCR synchronously on the just-uploaded document.
    Writes OCR text to document.search_text (FTS trigger fires automatically).
    NEVER writes decrypted file to disk — all processing in memory.
    Hard cap: skip OCR if page count > 50; set FAILED.
    """
    # TODO: implement using core/ocr.py
    raise NotImplementedError
```

Execution model options (choose one, document in the plan):
- **Inline (chosen for prototype):** simple, demos fine for 1–2 pages.
- `threading.Thread` after response returned: faster response, status shows PENDING briefly.
- `flask ocr-pending` CLI command: operator-run before demo.

---

## Implementation Order

1. Add OCR columns to documents migration (`ocr_status`, `ocr_confidence`, `ocr_language`, `ocr_page_count`)
2. Install tesseract + all five Indic language packs in Dockerfile
3. `backend/app/core/ocr.py` — `preprocess_image()`, `run_tesseract()`, `score_confidence()`
4. Wire `run_ocr_inline()` into upload pipeline in `document_service.py` (after chunks stored)
5. Verify OCR text reaches `Document.search_text` so FTS trigger picks it up
6. `PATCH /documents/{id}/ocr-text` — manual correction endpoint (LOW_CONFIDENCE case)
7. Frontend: OCR status badge on document cards; manual correction textarea
