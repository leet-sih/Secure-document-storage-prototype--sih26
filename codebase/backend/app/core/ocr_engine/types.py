"""Core data structures shared by every stage of the pipeline.

These types are the contract between the engines and the rest of the app.
Nothing outside `ocr.engines` should ever know which engine produced a result.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class ScriptKind(str, Enum):
    """How the text in a region was written."""

    PRINTED = "printed"
    HANDWRITTEN = "handwritten"
    UNKNOWN = "unknown"


class ReviewStatus(str, Enum):
    """Human review state. Nothing is indexed or hashed on-chain until APPROVED."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


@dataclass(frozen=True)
class BBox:
    """Axis-aligned box in pixel coordinates of the *preprocessed* page image.

    Origin is top-left, matching image conventions (not PDF conventions).
    """

    x: int
    y: int
    w: int
    h: int

    @property
    def x2(self) -> int:
        return self.x + self.w

    @property
    def y2(self) -> int:
        return self.y + self.h

    @property
    def area(self) -> int:
        return self.w * self.h

    def scaled(self, fx: float, fy: float) -> "BBox":
        return BBox(int(self.x * fx), int(self.y * fy), int(self.w * fx), int(self.h * fy))

    def union(self, other: "BBox") -> "BBox":
        x = min(self.x, other.x)
        y = min(self.y, other.y)
        return BBox(x, y, max(self.x2, other.x2) - x, max(self.y2, other.y2) - y)

    def intersects(self, other: "BBox") -> bool:
        return not (self.x2 <= other.x or other.x2 <= self.x or self.y2 <= other.y or other.y2 <= self.y)


@dataclass
class Word:
    """One recognised token with its position and the engine's confidence.

    `confidence` is normalised to 0.0-1.0 by every engine, so downstream code
    (the review queue threshold, the search indexer) never needs to know that
    Tesseract natively reports 0-100.
    """

    text: str
    bbox: BBox
    confidence: float
    engine: str = ""

    def __post_init__(self) -> None:
        self.confidence = max(0.0, min(1.0, float(self.confidence)))


@dataclass
class Region:
    """A detected text region (normally one line) routed to a single engine."""

    bbox: BBox
    script: ScriptKind = ScriptKind.UNKNOWN
    script_confidence: float = 0.0
    words: list[Word] = field(default_factory=list)
    engine: str = ""

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words if w.text)

    @property
    def confidence(self) -> float:
        """Mean word confidence, weighted by character count.

        Character weighting stops a stray one-letter token from dominating the
        score of an otherwise good line.
        """
        weights = [max(1, len(w.text)) for w in self.words]
        if not weights:
            return 0.0
        total = sum(weights)
        return sum(w.confidence * n for w, n in zip(self.words, weights)) / total


@dataclass
class PageResult:
    """Everything the pipeline knows about one page image."""

    page_index: int
    width: int
    height: int
    # Effective resolution of THIS page's image after preprocessing. The
    # searchable-PDF writer needs it to size the page; the review UI needs it
    # to show real-world measurements.
    dpi: int = 300
    dpi_is_known: bool = True
    regions: list[Region] = field(default_factory=list)
    source_path: str = ""
    rotation_applied: float = 0.0
    preprocess_notes: list[str] = field(default_factory=list)
    duration_ms: int = 0

    @property
    def text(self) -> str:
        return "\n".join(r.text for r in self.regions if r.text)

    @property
    def words(self) -> list[Word]:
        return [w for r in self.regions for w in r.words]

    @property
    def confidence(self) -> float:
        weights = [max(1, len(r.text)) for r in self.regions]
        if not weights or sum(weights) == 0:
            return 0.0
        return sum(r.confidence * n for r, n in zip(self.regions, weights)) / sum(weights)

    @property
    def low_confidence_regions(self) -> list[Region]:
        from .config import get_settings

        threshold = get_settings().review_confidence_threshold
        return [r for r in self.regions if r.confidence < threshold]


@dataclass
class DocumentResult:
    """The OCR output for one source file (image or multi-page PDF).

    This object is what the review UI reads and, once approved, what the
    indexer turns into HMAC keyword tokens. It deliberately holds no
    encryption keys and no wallet material.
    """

    document_id: str
    source_filename: str
    source_sha256: str
    pages: list[PageResult] = field(default_factory=list)
    review_status: ReviewStatus = ReviewStatus.PENDING
    engines_used: list[str] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def text(self) -> str:
        return "\n\n".join(p.text for p in self.pages)

    @property
    def confidence(self) -> float:
        if not self.pages:
            return 0.0
        weights = [max(1, len(p.text)) for p in self.pages]
        return sum(p.confidence * n for p, n in zip(self.pages, weights)) / sum(weights)

    @property
    def needs_review(self) -> bool:
        """Always True by design: this project requires human sign-off on every
        document before indexing. Kept as a property so the policy lives in one
        place if that ever loosens to threshold-based review."""
        return self.review_status is not ReviewStatus.APPROVED

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["review_status"] = self.review_status.value
        for page in d["pages"]:
            for region in page["regions"]:
                region["script"] = (
                    region["script"].value if isinstance(region["script"], ScriptKind) else region["script"]
                )
        d["confidence"] = round(self.confidence, 4)
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
