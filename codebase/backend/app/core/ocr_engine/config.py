"""Runtime settings, read from environment variables with safe defaults.

Two principles encoded here:

1. Offline by default. `OCR_ALLOW_NETWORK` is false unless explicitly set, and
   the transformers/HF libraries are put into offline mode at import time so a
   missing model fails loudly instead of silently downloading from the internet.
2. Hardware-agnostic. `resolve_device()` picks CUDA, then Apple MPS, then CPU,
   so the same image runs on a laptop and on a GPU server with no code change.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

_TRUE = {"1", "true", "yes", "on"}


def _flag(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in _TRUE


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _path(name: str, default: str) -> Path:
    return Path(os.environ.get(name, default)).expanduser()


@dataclass(frozen=True)
class Settings:
    # --- Offline enforcement -------------------------------------------------
    allow_network: bool = False
    model_dir: Path = field(default_factory=lambda: Path("./models"))

    # --- Ingestion -----------------------------------------------------------
    render_dpi: int = 300          # DPI used when rasterising PDF pages
    max_pixels: int = 40_000_000   # guard against decompression bombs
    max_pages: int = 500

    # --- Preprocessing -------------------------------------------------------
    deskew: bool = True
    denoise: bool = True
    max_skew_degrees: float = 15.0

    # --- Engines -------------------------------------------------------------
    device: str = "auto"           # auto | cpu | cuda | mps
    tesseract_lang: str = "eng"
    tesseract_cmd: str = "tesseract"
    trocr_model: str = "microsoft/trocr-base-handwritten"
    trocr_batch_size: int = 8
    enable_handwriting: bool = True

    # --- Routing -------------------------------------------------------------
    # Lines Tesseract reports below this confidence are re-examined by the
    # printed/handwritten classifier and may be re-run through TrOCR.
    reroute_confidence_threshold: float = 0.72
    classifier: str = "heuristic"  # heuristic | model | tag

    # --- Review --------------------------------------------------------------
    # Informational only: this project reviews every document regardless.
    # Used to highlight which regions the reviewer should look at first.
    review_confidence_threshold: float = 0.80

    @property
    def trocr_local_path(self) -> Path:
        """Where fetch_models.py places the handwriting model on disk."""
        return self.model_dir / self.trocr_model.replace("/", "__")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    s = Settings(
        allow_network=_flag("OCR_ALLOW_NETWORK", False),
        model_dir=_path("OCR_MODEL_DIR", "./models"),
        render_dpi=_int("OCR_RENDER_DPI", 300),
        max_pixels=_int("OCR_MAX_PIXELS", 40_000_000),
        max_pages=_int("OCR_MAX_PAGES", 500),
        deskew=_flag("OCR_DESKEW", True),
        denoise=_flag("OCR_DENOISE", True),
        max_skew_degrees=_float("OCR_MAX_SKEW_DEGREES", 15.0),
        device=os.environ.get("OCR_DEVICE", "auto"),
        tesseract_lang=os.environ.get("OCR_TESSERACT_LANG", "eng"),
        tesseract_cmd=os.environ.get("OCR_TESSERACT_CMD", "tesseract"),
        trocr_model=os.environ.get("OCR_TROCR_MODEL", "microsoft/trocr-base-handwritten"),
        trocr_batch_size=_int("OCR_TROCR_BATCH_SIZE", 8),
        enable_handwriting=_flag("OCR_ENABLE_HANDWRITING", True),
        reroute_confidence_threshold=_float("OCR_REROUTE_THRESHOLD", 0.72),
        classifier=os.environ.get("OCR_CLASSIFIER", "heuristic"),
        review_confidence_threshold=_float("OCR_REVIEW_THRESHOLD", 0.80),
    )
    _enforce_offline(s)
    return s


def _enforce_offline(s: Settings) -> None:
    """Put the ML stack into offline mode unless network is explicitly allowed.

    This is belt-and-braces: the Docker image also runs with no network. But a
    developer running the CLI directly on a laptop gets the same guarantee, and
    a typo in a model name fails with 'not found locally' rather than quietly
    uploading nothing but downloading gigabytes.
    """
    if s.allow_network:
        return
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
    os.environ.setdefault("HF_HOME", str(s.model_dir / ".hf"))


def resolve_device(preference: str | None = None) -> str:
    """Return the torch device string to use, without importing torch if we can.

    Called lazily by the handwriting engine only, so the typed-text path never
    pays the cost of importing torch.
    """
    pref = (preference or get_settings().device or "auto").lower()
    if pref != "auto":
        return pref
    try:
        import torch
    except ImportError:
        return "cpu"
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def describe_device() -> str:
    """Human-readable device summary, used by the CLI banner."""
    device = resolve_device()
    if device == "cuda":
        try:
            import torch

            return f"cuda ({torch.cuda.get_device_name(0)})"
        except Exception:
            return "cuda"
    if device == "mps":
        return "mps (Apple Silicon)"
    return "cpu"
