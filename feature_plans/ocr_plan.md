# Feature Plan: OCR-Based Document Digitisation (Future Roadmap)

> **Status:** Post-hackathon roadmap. Do NOT implement for the Sep 2 prototype.
> Prototype milestone: show a placeholder UI card "OCR — Coming Soon" in the upload flow.

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

## UI (Placeholder for Prototype)

For the Sep 2 prototype, show this in the document detail view:

```
[ OCR Status ]
  ⏳ OCR coming soon — this document is not yet text-searchable.
  Documents will be automatically indexed after OCR is enabled.
```

Do not implement the actual pipeline — just reserve the DB columns and the UI slot.

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

System packages (Docker):
```dockerfile
RUN apt-get install -y tesseract-ocr tesseract-ocr-hin tesseract-ocr-tam \
    poppler-utils libglib2.0-0 libsm6 libxrender1 libxext6
```

---

## Celery Task

```python
@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def process_ocr_task(self, document_id: str):
    try:
        document = Document.query.get(document_id)
        document.ocr_status = "IN_PROGRESS"
        db.session.commit()

        # Reconstruct document from chunks (full decryption)
        file_bytes = document_service.reconstruct_bytes(document_id)

        # Convert to images
        images = pdf_to_images(file_bytes, mime_type=document.mime_type)

        all_text = []
        confidences = []

        for img in images:
            processed = preprocess_image(img)
            data = pytesseract.image_to_data(
                processed,
                lang=document.ocr_language,
                output_type=pytesseract.Output.DICT
            )
            page_text = " ".join(w for w in data['text'] if w.strip())
            page_conf = [c for c in data['conf'] if c != -1]
            all_text.append(page_text)
            if page_conf:
                confidences.append(sum(page_conf) / len(page_conf))

        full_text = "\n\n".join(all_text)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0

        document.search_text = full_text
        document.ocr_confidence = avg_confidence / 100  # Tesseract gives 0-100
        document.ocr_page_count = len(images)
        document.ocr_status = (
            "DONE" if avg_confidence >= 80
            else "LOW_CONFIDENCE" if avg_confidence >= 60
            else "FAILED"
        )
        db.session.commit()

    except Exception as exc:
        document.ocr_status = "FAILED"
        db.session.commit()
        raise self.retry(exc=exc)
```

---

## Implementation Order (When Ready)

1. Add OCR columns to documents migration
2. Install tesseract + language packs in Docker image
3. `backend/app/core/ocr.py` — preprocess_image, run_tesseract, confidence scoring
4. `backend/app/tasks/ocr_task.py` — Celery task
5. Wire into upload pipeline: after upload completes, queue `process_ocr_task.delay(doc_id)`
6. `PATCH /documents/{id}/ocr-text` — manual correction endpoint
7. Frontend: OCR status badge on document cards; manual correction editor
