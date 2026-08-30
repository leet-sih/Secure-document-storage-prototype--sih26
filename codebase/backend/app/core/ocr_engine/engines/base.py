"""The engine contract.

Everything above this line in the stack (pipeline, review UI, search indexer)
talks only to `OCREngine`. That is what makes the Tesseract/TrOCR split an
implementation detail, and what will let Hindi models drop in later without
touching the pipeline.

Two capability flags let the router decide what an engine can be asked to do:

    supports_layout  - can find text regions on a full page by itself
    supports_script  - which kinds of writing it is any good at
"""

from __future__ import annotations

import abc
from dataclasses import dataclass

import numpy as np

from ..types import Region, ScriptKind


class EngineUnavailableError(RuntimeError):
    """The engine's dependencies or model weights are not present locally."""


@dataclass(frozen=True)
class EngineInfo:
    name: str
    version: str
    supports_layout: bool
    supports_script: frozenset[ScriptKind]
    device: str = "cpu"


class OCREngine(abc.ABC):
    """Base class for every recognition backend."""

    name: str = "base"

    @property
    @abc.abstractmethod
    def info(self) -> EngineInfo:
        """Describe this engine. Must not raise even if the model is missing."""

    @abc.abstractmethod
    def is_available(self) -> bool:
        """True if this engine can actually run right now, offline.

        Called before every use so a missing TrOCR checkpoint degrades to
        'typed-only mode' with a clear warning rather than crashing a batch job
        halfway through.
        """

    def detect_regions(self, image: np.ndarray) -> list[Region]:
        """Find text regions on a full page.

        Only engines with `supports_layout=True` implement this. Line-level
        recognisers such as TrOCR rely on another engine's layout output.
        """
        raise NotImplementedError(f"{self.name} does not perform layout analysis")

    @abc.abstractmethod
    def recognise(self, image: np.ndarray, regions: list[Region]) -> list[Region]:
        """Fill in `words` for each supplied region and return them.

        `image` is the full preprocessed page; region bboxes index into it.
        Implementations must return regions in the same order they arrived, with
        `engine` set and every word confidence normalised to 0.0-1.0.
        """

    def warmup(self) -> None:
        """Optional: load weights ahead of the first real page.

        Worth calling before a batch so the first document is not billed for a
        multi-second model load.
        """
        return None

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<{type(self).__name__} name={self.name!r} available={self.is_available()}>"


def crop(image: np.ndarray, region: Region, pad: int = 2) -> np.ndarray:
    """Cut a region out of the page, with a small pad and bounds clamping.

    The pad matters for handwriting: ascenders and descenders routinely spill
    a pixel or two outside a detected line box, and clipping them measurably
    hurts TrOCR.
    """
    h, w = image.shape[:2]
    b = region.bbox
    x1 = max(0, b.x - pad)
    y1 = max(0, b.y - pad)
    x2 = min(w, b.x2 + pad)
    y2 = min(h, b.y2 + pad)
    if x2 <= x1 or y2 <= y1:
        return np.zeros((1, 1), dtype=image.dtype)
    return image[y1:y2, x1:x2]
