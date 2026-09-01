"""Clean up a scanned page before OCR.

Order matters and is deliberate:

    grayscale -> denoise -> deskew -> upscale-if-tiny -> (binarise for analysis)

Deskew comes after denoise because the angle estimate is computed from the
binarised image, and salt-and-pepper noise skews that estimate. Upscaling comes
last so we do not spend time denoising pixels we are about to invent.

The colour/greyscale image is what gets fed to the OCR engines; the binarised
version is used only for layout analysis and the handwriting heuristics.
Tesseract 4+ and TrOCR both do better on greyscale than on hard-thresholded
input, so we never hand them the binary image.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from .config import get_settings

# Below this height, a text line has too few pixels for reliable recognition.
# 300 DPI text at 10pt is roughly 40px tall; we upscale anything under half that.
MIN_TARGET_LINE_HEIGHT = 20

# Skew search runs on an image downscaled to this longest edge. Large enough to
# keep line structure, small enough that ~50 rotations cost milliseconds.
SKEW_WORK_SIZE = 1000

# A connected component wider than this multiple of its height is a rule line,
# a table border or an underline - not a glyph.
MAX_GLYPH_ASPECT = 6.0


@dataclass
class PreprocessResult:
    """The cleaned page plus a record of what was done to it.

    `scale` and `rotation` are kept so bounding boxes computed on the processed
    image can be mapped back onto the original scan for the review UI and the
    searchable PDF overlay.
    """

    gray: np.ndarray
    binary: np.ndarray
    rotation: float = 0.0
    scale: float = 1.0
    notes: list[str] = field(default_factory=list)


def preprocess_page(image: np.ndarray) -> PreprocessResult:
    settings = get_settings()
    notes: list[str] = []

    gray = _to_gray(image)

    if settings.denoise:
        gray = _denoise(gray)
        notes.append("denoised")

    rotation = 0.0
    if settings.deskew:
        rotation = estimate_skew(gray, settings.max_skew_degrees)
        if abs(rotation) > 0.1:
            gray = rotate(gray, rotation)
            notes.append(f"deskewed {rotation:+.2f} deg")

    gray, scale = _upscale_if_small(gray)
    if scale != 1.0:
        notes.append(f"upscaled x{scale:.2f}")

    binary = binarise(gray)
    return PreprocessResult(gray=gray, binary=binary, rotation=rotation, scale=scale, notes=notes)


def _to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image
    if image.shape[2] == 4:
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _denoise(gray: np.ndarray) -> np.ndarray:
    """Median blur removes scanner speckle without softening stroke edges.

    A Gaussian blur would blur the strokes themselves, which costs accuracy on
    thin handwriting. Kernel 3 is intentionally conservative.
    """
    return cv2.medianBlur(gray, 3)


def binarise(gray: np.ndarray) -> np.ndarray:
    """Adaptive threshold. Returns text as white (255) on black (0).

    Adaptive rather than Otsu because scanned pages frequently have uneven
    lighting (shadow along the spine, vignetting from a phone camera) that a
    single global threshold handles badly.
    """
    inverted = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        blockSize=35,
        C=15,
    )
    return inverted


def estimate_skew(gray: np.ndarray, max_degrees: float = 15.0) -> float:
    """Estimate page skew in degrees. Positive = rotate by this much to straighten.

    Method: projection profile search. Binarise, then for each candidate angle
    rotate the image and measure the variance of the row-sum profile. When text
    lines are truly horizontal, rows alternate sharply between "full of ink" and
    "empty", so the variance peaks. The angle with the highest variance is the
    skew.

    This replaced a min-area-rectangle approach, which is faster but fails on
    exactly the pages that matter: any page with a figure, a table border, or a
    stamp gets one big component whose bounding rectangle has nothing to do with
    the text baselines. The projection profile only ever looks at ink density
    per row, so a figure adds noise but does not hijack the estimate.

    Search is coarse-to-fine (1 degree, then 0.1) and runs on a downscaled copy,
    which keeps it to a few milliseconds on a full page.
    """
    binary = binarise(gray)

    # Work small. Skew is a global property; full resolution buys nothing here
    # and costs ~30 warps of a 3500x2500 image.
    longest = max(binary.shape)
    if longest > SKEW_WORK_SIZE:
        scale = SKEW_WORK_SIZE / longest
        binary = cv2.resize(binary, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    # Drop anything too big to be a glyph before measuring. A stamp, a photo,
    # a table border or a scan edge is usually axis-aligned even when the text
    # is not, and it will happily out-vote the text and pull the estimate to 0.
    binary = _text_only_mask(binary)

    # Too little ink to say anything. 0.0 is the safe answer.
    if cv2.countNonZero(binary) < 50:
        return 0.0

    coarse = _best_angle(binary, np.arange(-max_degrees, max_degrees + 0.5, 1.0))
    fine = _best_angle(binary, np.arange(coarse - 1.0, coarse + 1.01, 0.1))

    if abs(fine) > max_degrees:
        return 0.0
    return float(round(fine, 2))


def _text_only_mask(binary: np.ndarray) -> np.ndarray:
    """Zero out connected components that are too large to be text.

    Thresholds are fractions of the page, so this is resolution-independent.
    Anything taller than 8% of the page height, or wider than half the page,
    is a figure, a rule or a border - never a character.
    """
    n_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if n_labels <= 1:
        return binary

    page_h, page_w = binary.shape[:2]
    max_h = max(4.0, page_h * 0.08)
    max_w = page_w * 0.5

    keep = np.zeros(n_labels, dtype=bool)
    for label in range(1, n_labels):
        h = stats[label, cv2.CC_STAT_HEIGHT]
        w = stats[label, cv2.CC_STAT_WIDTH]
        keep[label] = (h <= max_h) and (w <= max_w)

    if not keep[1:].any():
        return binary  # nothing survived: better to measure everything than nothing
    return np.where(keep[labels], binary, 0).astype(np.uint8)


def _best_angle(binary: np.ndarray, candidates: np.ndarray) -> float:
    """Return the candidate angle whose row-projection variance is highest."""
    best_angle, best_score = 0.0, -1.0
    for angle in candidates:
        score = _projection_score(binary, float(angle))
        if score > best_score:
            best_angle, best_score = float(angle), score
    return best_angle


def _projection_score(binary: np.ndarray, angle: float) -> float:
    """Variance of the horizontal ink profile after rotating by `angle`.

    Normalised by the mean so the score does not simply reward angles that keep
    more ink inside the (fixed-size) canvas.
    """
    if angle != 0.0:
        h, w = binary.shape[:2]
        matrix = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), angle, 1.0)
        rotated = cv2.warpAffine(
            binary, matrix, (w, h),
            flags=cv2.INTER_NEAREST,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )
    else:
        rotated = binary

    profile = rotated.sum(axis=1, dtype=np.float64)
    mean = profile.mean()
    if mean <= 0:
        return 0.0
    return float(profile.var() / mean)


def rotate(image: np.ndarray, degrees: float) -> np.ndarray:
    """Rotate about the centre, expanding the canvas so no text is clipped."""
    h, w = image.shape[:2]
    centre = (w / 2.0, h / 2.0)
    matrix = cv2.getRotationMatrix2D(centre, degrees, 1.0)

    cos, sin = abs(matrix[0, 0]), abs(matrix[0, 1])
    new_w = int(h * sin + w * cos)
    new_h = int(h * cos + w * sin)
    matrix[0, 2] += (new_w / 2) - centre[0]
    matrix[1, 2] += (new_h / 2) - centre[1]

    return cv2.warpAffine(
        image, matrix, (new_w, new_h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def _upscale_if_small(gray: np.ndarray) -> tuple[np.ndarray, float]:
    """Upscale low-resolution scans so text lines reach a workable height.

    Returns the image and the scale factor applied, so callers can map boxes
    back to original coordinates.
    """
    median_height = estimate_line_height(gray)
    if median_height <= 0 or median_height >= MIN_TARGET_LINE_HEIGHT:
        return gray, 1.0

    scale = min(4.0, MIN_TARGET_LINE_HEIGHT / median_height)
    resized = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return resized, float(scale)


def estimate_line_height(gray: np.ndarray) -> float:
    """Median height of connected components that look like text.

    Used both to decide whether to upscale and, later, as a normaliser for the
    handwriting heuristics so they are resolution-independent.
    """
    binary = binarise(gray)
    n_labels, _, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if n_labels <= 1:
        return 0.0

    heights = stats[1:, cv2.CC_STAT_HEIGHT]
    widths = stats[1:, cv2.CC_STAT_WIDTH]
    areas = stats[1:, cv2.CC_STAT_AREA]

    # Keep components that plausibly are glyphs: not dust, not full-page borders.
    page_h = gray.shape[0]
    # Aspect ratio is the discriminator, not absolute width: a glyph is at most
    # a few times wider than it is tall, while a rule line or table border is
    # tens of times wider. Filtering on width alone would keep horizontal rules.
    aspect = widths / np.maximum(1, heights)
    keep = (
        (heights > 4)
        & (heights < page_h * 0.1)
        & (areas > 12)
        & (aspect < MAX_GLYPH_ASPECT)
    )
    if not keep.any():
        return 0.0
    return float(np.median(heights[keep]))
