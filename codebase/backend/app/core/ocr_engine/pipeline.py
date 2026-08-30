"""Orchestration: file in, DocumentResult out.

The routing strategy, in order:

  1. Tesseract does one full-page pass. This gives line boxes AND a printed-text
     reading of every line, in a single cheap operation.
  2. Lines Tesseract read confidently are accepted as printed. Done - no further
     work, no model load.
  3. Lines below the reroute threshold go to the classifier. If it says
     handwritten, that line is re-recognised by TrOCR.

This costs one Tesseract pass plus TrOCR on only the suspect lines, rather than
running both engines over everything. On a typed page with a handwritten
signature block, TrOCR touches two or three lines instead of forty.

Nothing here writes to a database, encrypts anything, or touches a wallet. The
output is a plain object; storage, HMAC indexing and on-chain hashing are
downstream and deliberately separate.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .classify import Classifier, get_classifier
from .config import get_settings
from .engines import EngineUnavailableError, available_engines, get_engine
from .ingest import load_pages, load_pages_from_bytes, sha256_bytes, sha256_file
from .preprocess import preprocess_page
from .types import DocumentResult, PageResult, Region, ReviewStatus, ScriptKind

log = logging.getLogger(__name__)


@dataclass
class PipelineStats:
    """Per-run counters. Printed by the CLI; useful for tuning the threshold."""

    pages: int = 0
    regions: int = 0
    rerouted: int = 0
    handwritten: int = 0
    trocr_unavailable: bool = False


class OCRPipeline:
    def __init__(
        self,
        layout_engine: str = "tesseract",
        handwriting_engine: str = "trocr",
        classifier: Classifier | None = None,
    ) -> None:
        self.settings = get_settings()
        self.layout_engine_name = layout_engine
        self.handwriting_engine_name = handwriting_engine
        self.classifier = classifier or get_classifier()
        self.stats = PipelineStats()
        # When True, process_file retains the preprocessed page images in
        # `last_page_images`. The searchable-PDF writer needs exactly those
        # images, because the word boxes are in their coordinate space.
        # Off by default: holding a 200-page scan in RAM is not free.
        self.keep_page_images = False
        self.last_page_images: list[np.ndarray] = []

        self._layout = get_engine(layout_engine)
        if not self._layout.is_available():
            raise EngineUnavailableError(
                f"Layout engine '{layout_engine}' is not available. "
                "Install tesseract-ocr and pytesseract."
            )

        self._handwriting = get_engine(handwriting_engine)
        self._handwriting_ok = self._handwriting.is_available()
        if not self._handwriting_ok:
            self.stats.trocr_unavailable = True
            log.warning(
                "Handwriting engine '%s' unavailable - running in typed-only mode. "
                "Handwritten lines will be returned with low confidence and flagged "
                "for review, not silently dropped.",
                handwriting_engine,
            )

    # -- public API -----------------------------------------------------------

    def process_file(self, path: Path, document_id: str | None = None) -> DocumentResult:
        """Run the full pipeline over one image or PDF."""
        path = Path(path)
        doc = DocumentResult(
            document_id=document_id or uuid.uuid4().hex,
            source_filename=path.name,
            # Hashed from the raw bytes, before preprocessing. This is the value
            # that eventually goes on-chain.
            source_sha256=sha256_file(path),
            review_status=ReviewStatus.PENDING,
        )

        engines_seen: set[str] = set()
        self.last_page_images = []
        for source_page in load_pages(path):
            page = self.process_page(
                source_page.image,
                source_page.index,
                str(path),
                dpi=source_page.dpi,
                dpi_is_known=source_page.dpi_is_known,
            )
            doc.pages.append(page)
            engines_seen.update(r.engine for r in page.regions if r.engine)
            if self.keep_page_images:
                self.last_page_images.append(self._last_prepared)

        doc.engines_used = sorted(engines_seen)
        doc.meta.update(self._run_meta())
        return doc

    def _run_meta(self) -> dict:
        """What the run was configured with. Recorded on every document so a
        result can be explained months later."""
        return {
            "device": self._handwriting.info.device if self._handwriting_ok else "cpu",
            "handwriting_available": self._handwriting_ok,
            "classifier": self.settings.classifier,
            "reroute_threshold": self.settings.reroute_confidence_threshold,
        }

    def process_bytes(
        self,
        data: bytes,
        filename: str,
        document_id: str | None = None,
    ) -> DocumentResult:
        """Run the full pipeline over a document held only in memory.

        Same contract as process_file, for callers that must not write the
        plaintext to disk -- typically because they decrypted it to read it, and
        a temp file would leave a decrypted copy behind for anyone with access
        to the box or a crash dump.

        The SHA-256 is still taken from the raw bytes before any preprocessing,
        so it matches what process_file would produce for the same document.
        """
        label = Path(filename or "document")
        doc = DocumentResult(
            document_id=document_id or uuid.uuid4().hex,
            source_filename=label.name,
            source_sha256=sha256_bytes(data),
            review_status=ReviewStatus.PENDING,
        )

        engines_seen: set[str] = set()
        self.last_page_images = []
        for source_page in load_pages_from_bytes(data, filename):
            page = self.process_page(
                source_page.image,
                source_page.index,
                # Not a readable path: the document exists only in memory.
                f"memory://{label.name}",
                dpi=source_page.dpi,
                dpi_is_known=source_page.dpi_is_known,
            )
            doc.pages.append(page)
            engines_seen.update(r.engine for r in page.regions if r.engine)
            if self.keep_page_images:
                self.last_page_images.append(self._last_prepared)

        doc.engines_used = sorted(engines_seen)
        doc.meta.update(self._run_meta())
        return doc

    def process_page(
        self,
        image: np.ndarray,
        index: int = 0,
        source_path: str = "",
        dpi: int = 300,
        dpi_is_known: bool = True,
    ) -> PageResult:
        started = time.perf_counter()

        prep = preprocess_page(image)
        self._last_prepared = prep.gray
        page = PageResult(
            page_index=index,
            width=prep.gray.shape[1],
            height=prep.gray.shape[0],
            # Preprocessing may have upscaled a low-resolution scan. The boxes
            # are in the upscaled image's pixels, so the effective DPI scales
            # with it or the searchable PDF comes out the wrong physical size.
            dpi=max(1, int(round(dpi * prep.scale))),
            dpi_is_known=dpi_is_known,
            source_path=source_path,
            rotation_applied=prep.rotation,
            preprocess_notes=list(prep.notes),
        )

        # Step 1: one Tesseract pass gives layout + a printed reading.
        regions = self._layout.detect_regions(prep.gray)
        self.stats.regions += len(regions)

        confident, suspect = self._split_by_confidence(regions)
        for region in confident:
            region.script = ScriptKind.PRINTED
            region.script_confidence = 1.0

        # Step 2: only suspect lines get classified.
        handwritten: list[Region] = []
        for region in suspect:
            decision = self.classifier.classify(prep.gray, region)
            region.script = decision.script
            region.script_confidence = decision.confidence
            if decision.script is ScriptKind.HANDWRITTEN:
                handwritten.append(region)

        self.stats.rerouted += len(suspect)
        self.stats.handwritten += len(handwritten)

        # Step 3: re-recognise handwritten lines, if we can.
        if handwritten and self._handwriting_ok:
            try:
                self._handwriting.recognise(prep.gray, handwritten)
            except EngineUnavailableError as exc:
                # Keep the Tesseract reading rather than losing the line entirely.
                log.warning("Handwriting pass failed, keeping typed reading: %s", exc)

        page.regions = sorted(regions, key=lambda r: (r.bbox.y, r.bbox.x))
        page.duration_ms = int((time.perf_counter() - started) * 1000)
        self.stats.pages += 1
        return page

    # -- internals ------------------------------------------------------------

    def _split_by_confidence(self, regions: list[Region]) -> tuple[list[Region], list[Region]]:
        """Partition into (trust Tesseract, needs a second look)."""
        threshold = self.settings.reroute_confidence_threshold
        confident, suspect = [], []
        for region in regions:
            (confident if region.confidence >= threshold else suspect).append(region)
        return confident, suspect


def describe_environment() -> str:
    """One-line summary of what is actually runnable. Used by the CLI banner."""
    from .config import describe_device

    engines = available_engines()
    if not engines:
        return "No OCR engines available."
    parts = [f"{name} v{info.version} [{info.device}]" for name, info in engines.items()]
    return f"device={describe_device()}  engines: " + ", ".join(parts)
