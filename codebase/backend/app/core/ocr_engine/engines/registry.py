"""Engine lookup, so nothing else in the codebase imports a concrete backend.

Adding Hindi later is a two-line change here: register the new engine under a
name and declare which ScriptKind it serves. The pipeline, the review UI and the
indexer need no changes.
"""

from __future__ import annotations

from typing import Callable

from .base import EngineInfo, EngineUnavailableError, OCREngine
from .tesseract_engine import TesseractEngine
from .trocr_engine import TrOCREngine

_BUILDERS: dict[str, Callable[[], OCREngine]] = {
    "tesseract": TesseractEngine,
    "trocr": TrOCREngine,
}

_CACHE: dict[str, OCREngine] = {}


def register(name: str, builder: Callable[[], OCREngine]) -> None:
    """Add a backend at runtime (used by tests and by future language packs)."""
    _BUILDERS[name] = builder
    _CACHE.pop(name, None)


def get_engine(name: str) -> OCREngine:
    """Return a shared instance of the named engine.

    Instances are cached because model loading is expensive and the engines are
    stateless with respect to the pages they process.
    """
    if name not in _BUILDERS:
        raise KeyError(f"Unknown engine '{name}'. Known: {', '.join(sorted(_BUILDERS))}")
    if name not in _CACHE:
        _CACHE[name] = _BUILDERS[name]()
    return _CACHE[name]


def available_engines() -> dict[str, EngineInfo]:
    """Report which backends can actually run right now, offline.

    The CLI prints this at startup so it is obvious when handwriting support is
    silently missing.
    """
    out: dict[str, EngineInfo] = {}
    for name in sorted(_BUILDERS):
        engine = get_engine(name)
        if engine.is_available():
            out[name] = engine.info
    return out


def reset_cache() -> None:
    """Drop cached instances. Frees model memory; mainly for tests."""
    _CACHE.clear()


__all__ = [
    "OCREngine",
    "EngineInfo",
    "EngineUnavailableError",
    "get_engine",
    "available_engines",
    "register",
    "reset_cache",
]
