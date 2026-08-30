"""Turn a source file into a list of page images.

Handles the two input types this project accepts: single-page JPG/PNG and
multi-page scanned PDFs. PDFs are rasterised with pypdfium2, which bundles its
own renderer, so there is no poppler/system dependency to install and nothing
shells out to a binary that might phone home.

Every file is hashed on the way in. That SHA-256 is the same value that later
goes on-chain, so it is computed once, from the raw bytes, before any
preprocessing touches the pixels.
"""

from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Union

import numpy as np
from PIL import Image

from .config import get_settings

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
PDF_SUFFIXES = {".pdf"}
SUPPORTED_SUFFIXES = IMAGE_SUFFIXES | PDF_SUFFIXES

# Pillow refuses very large images by default as a decompression-bomb guard.
# We raise it to our own configured ceiling rather than disabling it.
Image.MAX_IMAGE_PIXELS = get_settings().max_pixels


class UnsupportedFileError(ValueError):
    """Raised for a file type the pipeline does not accept."""


@dataclass
class SourcePage:
    """One page image, still in its original (un-preprocessed) form.

    `dpi` is carried through the whole pipeline because the searchable-PDF
    writer needs it to size pages correctly. For PDFs we know it exactly (we
    chose the render scale). For images we read the EXIF/JFIF density if the
    scanner recorded one, and fall back to the configured default otherwise -
    a guess, but a documented one.
    """

    index: int
    image: np.ndarray  # grayscale or BGR uint8
    source_path: Path
    dpi: int = 300
    dpi_is_known: bool = False
    # True when the page came from bytes rather than a file. `source_path` is
    # then only a label -- the original filename -- and nothing on disk. Callers
    # that re-read the source (the review queue does, to cut crops) must check
    # this rather than trusting the path to exist.
    from_memory: bool = False


def sha256_bytes(data: bytes) -> str:
    """The same digest as sha256_file, for input that never touches disk."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    """Stream the file through SHA-256 so a large PDF never lands in memory."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_SUFFIXES


def load_pages(path: Path) -> Iterator[SourcePage]:
    """Yield page images for `path`, one at a time.

    Yielding rather than returning a list matters for multi-page PDFs: a
    200-page scan at 300 DPI would otherwise hold several GB of raw pixels in
    memory at once.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        yield from _load_image(path, path, False)
    elif suffix in PDF_SUFFIXES:
        yield from _load_pdf(path, path, False)
    else:
        raise UnsupportedFileError(
            f"{path.name}: unsupported type '{suffix}'. "
            f"Accepted: {', '.join(sorted(SUPPORTED_SUFFIXES))}"
        )


def _load_image(source: Union[Path, bytes], label: Path, in_memory: bool) -> Iterator[SourcePage]:
    handle = io.BytesIO(source) if isinstance(source, bytes) else source
    with Image.open(handle) as img:
        # EXIF orientation is common in phone photos; apply it before anything
        # else so deskew is not fighting a 90-degree rotation flag.
        from PIL import ImageOps

        img = ImageOps.exif_transpose(img)
        arr = np.array(img.convert("L"))
        dpi, known = _image_dpi(img)
    yield SourcePage(index=0, image=arr, source_path=label, dpi=dpi,
                     dpi_is_known=known, from_memory=in_memory)


def _image_dpi(img: "Image.Image") -> tuple[int, bool]:
    """Read the scanner-recorded resolution, if there is one.

    Returns (dpi, is_known). Values outside 50-1200 are treated as junk - some
    tools write 1 or 0 - and fall back to the configured default.
    """
    raw = img.info.get("dpi")
    if isinstance(raw, (tuple, list)) and raw:
        try:
            value = int(round(float(raw[0])))
        except (TypeError, ValueError):
            value = 0
        if 50 <= value <= 1200:
            return value, True
    return get_settings().render_dpi, False


def _load_pdf(source: Union[Path, bytes], label: Path, in_memory: bool) -> Iterator[SourcePage]:
    settings = get_settings()
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError(
            "Reading PDFs requires pypdfium2. Install it with: pip install pypdfium2"
        ) from exc

    scale = settings.render_dpi / 72.0  # PDF user space is 72 units per inch
    # pypdfium2 opens raw bytes directly, so an in-memory PDF never needs a
    # temporary file. That matters where the plaintext must not reach disk.
    doc = pdfium.PdfDocument(source if isinstance(source, bytes) else str(source))
    try:
        n_pages = min(len(doc), settings.max_pages)
        for i in range(n_pages):
            page = doc[i]
            bitmap = page.render(scale=scale, grayscale=True)
            arr = np.asarray(bitmap.to_pil().convert("L"))
            yield SourcePage(
                index=i, image=arr, source_path=label,
                dpi=settings.render_dpi, dpi_is_known=True, from_memory=in_memory,
            )
            bitmap.close()
            page.close()
    finally:
        doc.close()


def load_pages_from_bytes(data: bytes, filename: str) -> Iterator[SourcePage]:
    """Yield page images for a document held only in memory.

    Exists for callers that must never write the plaintext to disk -- a system
    that decrypts a document to read it, and would otherwise leave a decrypted
    copy in a temp directory for the OCR to open. The file type is taken from
    `filename`, since bytes carry no extension.
    """
    label = Path(filename or "document")
    suffix = label.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        yield from _load_image(data, label, True)
    elif suffix in PDF_SUFFIXES:
        yield from _load_pdf(data, label, True)
    else:
        raise UnsupportedFileError(
            f"{label.name}: unsupported type '{suffix}'. "
            f"Accepted: {', '.join(sorted(SUPPORTED_SUFFIXES))}"
        )


def iter_source_files(root: Path, recursive: bool = True) -> Iterator[Path]:
    """Find every supported file under `root`, sorted for reproducible runs."""
    root = Path(root)
    if root.is_file():
        if is_supported(root):
            yield root
        return
    pattern = "**/*" if recursive else "*"
    for candidate in sorted(root.glob(pattern)):
        if candidate.is_file() and is_supported(candidate):
            yield candidate
