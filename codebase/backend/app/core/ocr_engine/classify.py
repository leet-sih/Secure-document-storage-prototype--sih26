"""Decide, per text line, whether it is printed or handwritten.

Be clear about what this is: a feature-based heuristic, not a trained model. It
is honest about that in its confidence scores, and it exists so the pipeline is
complete and testable end to end today. A small CNN trained on your own scans
will beat it, and `ModelClassifier` below is the slot it drops into.

The heuristic combines four signals, each cheap to compute and each capturing a
real, documented difference between print and handwriting:

  1. Tesseract's own confidence. It is a printed-text recogniser; when it reads
     a line badly, that line is often not printed text. Strongest single signal.
  2. Baseline jitter. Printed glyphs sit on a shared baseline within a pixel or
     two. Handwriting wanders.
  3. Height variance. Printed characters of the same case are near-identical in
     height. Handwritten ones are not.
  4. Stroke-width variance. Print uses one consistent stroke weight per font.
     Pen pressure and speed vary within a single handwritten word.

Signals 2-4 are normalised by the line's own height, so they are independent of
scan resolution.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .config import get_settings
from .engines.base import crop
from .types import Region, ScriptKind

# Weights were chosen so that Tesseract confidence dominates but cannot decide
# alone; a clean printed line with an unusual font should not be misrouted.
WEIGHTS = {
    "tesseract_conf": 0.45,
    "baseline_jitter": 0.20,
    "height_variance": 0.20,
    "stroke_variance": 0.15,
}

# Score above this => handwritten. Set slightly above 0.5 because misrouting
# print to TrOCR is the more expensive mistake (slow, and TrOCR is worse at print).
HANDWRITTEN_THRESHOLD = 0.55


@dataclass
class ScriptDecision:
    script: ScriptKind
    confidence: float
    features: dict[str, float]


class Classifier:
    """Interface. Swap the implementation via OCR_CLASSIFIER."""

    def classify(self, image: np.ndarray, region: Region) -> ScriptDecision:
        raise NotImplementedError


class TagClassifier(Classifier):
    """Trusts an uploader-supplied label. Used when OCR_CLASSIFIER=tag.

    The label is read from `region.script` if already set, otherwise everything
    is treated as printed.
    """

    def classify(self, image: np.ndarray, region: Region) -> ScriptDecision:
        script = region.script if region.script is not ScriptKind.UNKNOWN else ScriptKind.PRINTED
        return ScriptDecision(script=script, confidence=1.0, features={})


class HeuristicClassifier(Classifier):
    """Feature-based printed/handwritten discrimination. See module docstring."""

    def classify(self, image: np.ndarray, region: Region) -> ScriptDecision:
        patch = crop(image, region, pad=2)
        features = {
            "tesseract_conf": self._tesseract_signal(region),
            "baseline_jitter": self._baseline_jitter(patch),
            "height_variance": self._height_variance(patch),
            "stroke_variance": self._stroke_variance(patch),
        }
        # Each feature is already oriented so that higher == more handwritten.
        score = sum(WEIGHTS[k] * v for k, v in features.items())

        script = ScriptKind.HANDWRITTEN if score >= HANDWRITTEN_THRESHOLD else ScriptKind.PRINTED
        # Confidence is distance from the decision boundary, rescaled to 0-1.
        margin = abs(score - HANDWRITTEN_THRESHOLD)
        confidence = min(1.0, margin / max(HANDWRITTEN_THRESHOLD, 1 - HANDWRITTEN_THRESHOLD))
        return ScriptDecision(script=script, confidence=confidence, features=features)

    # -- individual signals ---------------------------------------------------

    @staticmethod
    def _tesseract_signal(region: Region) -> float:
        """Low Tesseract confidence -> likely handwritten. Returns 0-1."""
        if not region.words:
            return 0.8  # detected a line but read nothing: suspicious
        return 1.0 - region.confidence

    @staticmethod
    def _components(patch: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Connected components that plausibly are glyphs, plus the binary image."""
        from .preprocess import binarise

        binary = binarise(patch)
        n, _, stats, centroids = cv2.connectedComponentsWithStats(binary, connectivity=8)
        if n <= 1:
            return np.empty((0, 5), dtype=np.int32), binary

        stats = stats[1:]
        h = patch.shape[0]
        keep = (
            (stats[:, cv2.CC_STAT_HEIGHT] > max(2, h * 0.12))
            & (stats[:, cv2.CC_STAT_HEIGHT] < h * 1.2)
            & (stats[:, cv2.CC_STAT_AREA] > 6)
        )
        return stats[keep], binary

    def _baseline_jitter(self, patch: np.ndarray) -> float:
        """Std-dev of glyph bottoms, normalised by line height. 0-1."""
        stats, _ = self._components(patch)
        if len(stats) < 4:
            return 0.5  # too little evidence: stay neutral
        bottoms = stats[:, cv2.CC_STAT_TOP] + stats[:, cv2.CC_STAT_HEIGHT]
        jitter = float(np.std(bottoms)) / max(1.0, patch.shape[0])
        # ~0.05 is typical for print, ~0.20+ for handwriting.
        return float(np.clip((jitter - 0.04) / 0.16, 0.0, 1.0))

    def _height_variance(self, patch: np.ndarray) -> float:
        """Coefficient of variation of glyph heights. 0-1."""
        stats, _ = self._components(patch)
        if len(stats) < 4:
            return 0.5
        heights = stats[:, cv2.CC_STAT_HEIGHT].astype(float)
        mean = heights.mean()
        if mean <= 0:
            return 0.5
        cv_ = float(heights.std() / mean)
        # ~0.15 typical for print (ascenders/descenders), ~0.40+ for handwriting.
        return float(np.clip((cv_ - 0.15) / 0.30, 0.0, 1.0))

    def _stroke_variance(self, patch: np.ndarray) -> float:
        """Variation in stroke thickness, measured by distance transform. 0-1.

        The distance transform of the text mask gives, at each ink pixel, the
        distance to the nearest background pixel. Local maxima along the stroke
        skeleton are half the stroke width, so their spread is a direct measure
        of how uniform the pen/font weight is.
        """
        from .preprocess import binarise

        binary = binarise(patch)
        if binary.sum() == 0:
            return 0.5
        dist = cv2.distanceTransform(binary, cv2.DIST_L2, 3)
        widths = dist[dist > 0.5]
        if widths.size < 20:
            return 0.5
        mean = float(widths.mean())
        if mean <= 0:
            return 0.5
        cv_ = float(widths.std() / mean)
        # ~0.35 typical for print, ~0.60+ for pen strokes.
        return float(np.clip((cv_ - 0.35) / 0.30, 0.0, 1.0))


class ModelClassifier(Classifier):
    """Placeholder for a trained printed/handwritten CNN.

    Not implemented. Kept so the swap is a config change, not a refactor. Train
    on crops from your own approved documents once the review queue has produced
    a labelled set - that data is the reason the review step exists.
    """

    def classify(self, image: np.ndarray, region: Region) -> ScriptDecision:
        raise NotImplementedError(
            "No trained script classifier yet. Use OCR_CLASSIFIER=heuristic. "
            "Labelled training crops come out of the review queue."
        )


def get_classifier(name: str | None = None) -> Classifier:
    choice = (name or get_settings().classifier).lower()
    if choice == "heuristic":
        return HeuristicClassifier()
    if choice == "tag":
        return TagClassifier()
    if choice == "model":
        return ModelClassifier()
    raise ValueError(f"Unknown classifier '{choice}'. Use: heuristic | tag | model")
