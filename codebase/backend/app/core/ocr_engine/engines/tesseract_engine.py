"""Tesseract backend: the fast path for typed text, and the layout detector.

Tesseract earns two jobs in this pipeline:

1. Recognising printed text. It is very good at this, needs ~50 MB of RAM, and
   runs in milliseconds per page on a CPU.
2. Finding text lines on the page. Its layout analysis (LSTM page segmentation)
   gives us line boxes for free during the same pass, which we then reuse to
   route handwritten lines to TrOCR. Adding a separate detector model would
   cost hundreds of MB for no accuracy gain on document scans.

Tesseract cannot read cursive handwriting - it is a printed-text recogniser.
Its low confidence on a handwritten line is the signal we use to reroute, not a
bug to be tuned away.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Any

import numpy as np

from ..config import get_settings
from ..types import BBox, Region, ScriptKind, Word
from .base import EngineInfo, EngineUnavailableError, OCREngine

# Tesseract page segmentation modes we care about.
PSM_AUTO = 3          # full automatic page segmentation - used for layout
PSM_SINGLE_LINE = 7   # treat the crop as one text line - used for re-recognition

# Tesseract emits -1 for non-text layout rows; anything below this is noise.
MIN_WORD_CONFIDENCE = 0.0


class TesseractEngine(OCREngine):
    name = "tesseract"

    def __init__(self, lang: str | None = None, cmd: str | None = None) -> None:
        settings = get_settings()
        self.lang = lang or settings.tesseract_lang
        self.cmd = cmd or settings.tesseract_cmd
        self._available: bool | None = None
        self._version: str = "unknown"

    # -- availability ---------------------------------------------------------

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        self._available = False
        try:
            import pytesseract  # noqa: F401
        except ImportError:
            return False
        if shutil.which(self.cmd) is None:
            return False
        try:
            out = subprocess.run(
                [self.cmd, "--version"], capture_output=True, text=True, timeout=10
            )
            self._version = out.stdout.splitlines()[0].split()[-1] if out.stdout else "unknown"
        except (OSError, subprocess.SubprocessError, IndexError):
            return False
        self._available = True
        return True

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(
            name=self.name,
            version=self._version,
            supports_layout=True,
            supports_script=frozenset({ScriptKind.PRINTED}),
            device="cpu",
        )

    # -- layout ---------------------------------------------------------------

    def detect_regions(self, image: np.ndarray) -> list[Region]:
        """Return one Region per text line found on the page.

        We ask Tesseract for word-level data and group by its (block, paragraph,
        line) identifiers rather than doing our own line clustering, because its
        grouping already accounts for columns and reading order.
        """
        data = self._image_to_data(image, psm=PSM_AUTO)
        lines = self._group_words_by_line(data)

        regions: list[Region] = []
        for words in lines.values():
            if not words:
                continue
            bbox = words[0].bbox
            for w in words[1:]:
                bbox = bbox.union(w.bbox)
            regions.append(
                Region(bbox=bbox, script=ScriptKind.UNKNOWN, words=words, engine=self.name)
            )
        regions.sort(key=lambda r: (r.bbox.y, r.bbox.x))
        return regions

    # -- recognition ----------------------------------------------------------

    def recognise(self, image: np.ndarray, regions: list[Region]) -> list[Region]:
        """Re-run recognition on specific regions in single-line mode.

        Used when a region was detected by one pass but needs recognising by
        this engine specifically (for example a line the classifier decided was
        printed after all).
        """
        if not self.is_available():
            raise EngineUnavailableError("tesseract binary or pytesseract not found")

        from .base import crop

        out: list[Region] = []
        for region in regions:
            patch = crop(image, region)
            data = self._image_to_data(patch, psm=PSM_SINGLE_LINE)
            words: list[Word] = []
            for w in self._words_from_data(data):
                # Shift box from crop-local coordinates back to page coordinates.
                shifted = BBox(
                    w.bbox.x + region.bbox.x - 2,
                    w.bbox.y + region.bbox.y - 2,
                    w.bbox.w,
                    w.bbox.h,
                )
                words.append(Word(text=w.text, bbox=shifted, confidence=w.confidence, engine=self.name))
            region.words = words
            region.engine = self.name
            out.append(region)
        return out

    # -- internals ------------------------------------------------------------

    def _image_to_data(self, image: np.ndarray, psm: int) -> dict[str, Any]:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = self.cmd
        config = f"--psm {psm} --oem 1"  # oem 1 = LSTM engine only
        return pytesseract.image_to_data(
            image,
            lang=self.lang,
            config=config,
            output_type=pytesseract.Output.DICT,
        )

    def _words_from_data(self, data: dict[str, Any]) -> list[Word]:
        words: list[Word] = []
        for i, text in enumerate(data.get("text", [])):
            text = (text or "").strip()
            if not text:
                continue
            raw_conf = float(data["conf"][i])
            if raw_conf < 0:  # -1 marks a layout row, not a recognised word
                continue
            words.append(
                Word(
                    text=text,
                    bbox=BBox(
                        int(data["left"][i]),
                        int(data["top"][i]),
                        int(data["width"][i]),
                        int(data["height"][i]),
                    ),
                    confidence=raw_conf / 100.0,  # normalise 0-100 -> 0.0-1.0
                    engine=self.name,
                )
            )
        return words

    def _group_words_by_line(self, data: dict[str, Any]) -> dict[tuple, list[Word]]:
        lines: dict[tuple, list[Word]] = {}
        for i, text in enumerate(data.get("text", [])):
            text = (text or "").strip()
            if not text:
                continue
            raw_conf = float(data["conf"][i])
            if raw_conf < 0:
                continue
            key = (
                data["page_num"][i],
                data["block_num"][i],
                data["par_num"][i],
                data["line_num"][i],
            )
            lines.setdefault(key, []).append(
                Word(
                    text=text,
                    bbox=BBox(
                        int(data["left"][i]),
                        int(data["top"][i]),
                        int(data["width"][i]),
                        int(data["height"][i]),
                    ),
                    confidence=raw_conf / 100.0,
                    engine=self.name,
                )
            )
        return lines
