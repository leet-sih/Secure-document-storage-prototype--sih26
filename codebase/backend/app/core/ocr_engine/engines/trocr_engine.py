"""TrOCR backend: the handwriting path.

TrOCR is a line-level model. It takes an image of exactly one text line and
emits a string - it has no concept of a page, no layout analysis, and no word
boundaries. That shapes everything here:

  * It only ever runs on crops that Tesseract's layout pass already isolated.
  * It cannot give per-word boxes, so we distribute the line box across the
    returned tokens proportionally by character width. Those boxes are
    approximate and are marked as such in `Word.engine`; they are good enough
    to highlight a search hit on a scan, and must not be treated as ground
    truth for anything precise.
  * It has no native confidence score, so we derive one from the mean token
    log-probability of the generated sequence.

Weights are loaded strictly from the local model directory. If they are not
there, this engine reports unavailable and the pipeline continues in
typed-only mode rather than reaching out to the internet.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from ..config import get_settings, resolve_device
from ..types import BBox, Region, ScriptKind, Word
from .base import EngineInfo, EngineUnavailableError, OCREngine, crop

# TrOCR's vision encoder expects roughly this aspect ratio for a text line.
# Very short crops (a single character) and very long ones both degrade; we
# clamp rather than reject, since a bad read is more useful than a dropped line.
MIN_CROP_HEIGHT = 8
MIN_CROP_WIDTH = 8


class TrOCREngine(OCREngine):
    name = "trocr"

    def __init__(self, model_path: str | None = None, device: str | None = None) -> None:
        settings = get_settings()
        self.model_path = model_path or str(settings.trocr_local_path)
        self.batch_size = settings.trocr_batch_size
        self._device = device
        self._processor: Any = None
        self._model: Any = None
        self._available: bool | None = None

    # -- availability ---------------------------------------------------------

    def is_available(self) -> bool:
        """Check dependencies and local weights without loading the model.

        Deliberately cheap: this is called on every page, and loading a 1.3 GB
        checkpoint to answer 'can you run?' would be absurd.
        """
        if self._available is not None:
            return self._available
        self._available = False

        if not get_settings().enable_handwriting:
            return False
        try:
            import torch  # noqa: F401
            import transformers  # noqa: F401
        except ImportError:
            return False

        from pathlib import Path

        path = Path(self.model_path)
        # A HuggingFace snapshot always has a config.json at its root.
        if not (path / "config.json").is_file():
            return False

        self._available = True
        return True

    @property
    def device(self) -> str:
        if self._device is None:
            self._device = resolve_device()
        return self._device

    @property
    def info(self) -> EngineInfo:
        return EngineInfo(
            name=self.name,
            version=get_settings().trocr_model,
            supports_layout=False,
            supports_script=frozenset({ScriptKind.HANDWRITTEN}),
            device=self.device,
        )

    # -- model loading --------------------------------------------------------

    def warmup(self) -> None:
        self._ensure_loaded()

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        if not self.is_available():
            raise EngineUnavailableError(
                f"TrOCR weights not found at {self.model_path}. "
                "Run scripts/fetch_models.py once on a networked machine, then copy "
                "the models/ directory across."
            )
        import torch
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel

        self._processor = TrOCRProcessor.from_pretrained(self.model_path, local_files_only=True)
        model = VisionEncoderDecoderModel.from_pretrained(self.model_path, local_files_only=True)
        model.eval()
        # float16 halves memory and roughly doubles throughput on CUDA. On CPU
        # and MPS it is slower or unsupported, so we keep float32 there.
        if self.device == "cuda":
            model = model.half()
        self._model = model.to(self.device)
        torch.set_grad_enabled(False)

    # -- recognition ----------------------------------------------------------

    def recognise(self, image: np.ndarray, regions: list[Region]) -> list[Region]:
        if not regions:
            return []
        self._ensure_loaded()

        import torch
        from PIL import Image

        results: list[Region] = []
        for start in range(0, len(regions), self.batch_size):
            batch = regions[start : start + self.batch_size]
            crops = []
            usable: list[Region] = []
            for region in batch:
                patch = crop(image, region, pad=4)
                if patch.shape[0] < MIN_CROP_HEIGHT or patch.shape[1] < MIN_CROP_WIDTH:
                    region.words = []
                    region.engine = self.name
                    results.append(region)
                    continue
                # TrOCR's processor expects RGB; our pipeline is grayscale.
                crops.append(Image.fromarray(patch).convert("RGB"))
                usable.append(region)

            if not usable:
                continue

            pixel_values = self._processor(images=crops, return_tensors="pt").pixel_values
            if self.device == "cuda":
                pixel_values = pixel_values.half()
            pixel_values = pixel_values.to(self.device)

            with torch.inference_mode():
                generated = self._model.generate(
                    pixel_values,
                    max_new_tokens=128,
                    num_beams=1,               # greedy: beams cost time for little gain here
                    output_scores=True,
                    return_dict_in_generate=True,
                )

            texts = self._processor.batch_decode(generated.sequences, skip_special_tokens=True)
            confidences = self._sequence_confidences(generated)

            for region, text, conf in zip(usable, texts, confidences):
                region.words = self._split_into_words(text.strip(), region.bbox, conf)
                region.engine = self.name
                region.script = ScriptKind.HANDWRITTEN
                results.append(region)

        # Preserve the caller's ordering.
        order = {id(r): i for i, r in enumerate(regions)}
        results.sort(key=lambda r: order[id(r)])
        return results

    # -- internals ------------------------------------------------------------

    def _special_token_ids(self) -> tuple[int | None, int | None]:
        """Find (eos, pad) wherever this model keeps them.

        VisionEncoderDecoderModel leaves eos_token_id and pad_token_id as None on
        the TOP-level config and sets them on the decoder config and the
        generation config instead. Reading only the top level silently yields
        (None, None), which disables the padding guard below without failing --
        the bug looks fixed and is not. Check every location.
        """
        candidates = (
            getattr(self._model, "generation_config", None),
            getattr(getattr(self._model, "config", None), "decoder", None),
            getattr(self._model, "config", None),
        )
        eos = pad = None
        for source in candidates:
            if source is None:
                continue
            if eos is None:
                eos = getattr(source, "eos_token_id", None)
            if pad is None:
                pad = getattr(source, "pad_token_id", None)
        return eos, pad

    def _sequence_confidences(self, generated: Any) -> list[float]:
        """Turn generation scores into one 0-1 confidence per sequence.

        We average the per-step log-probability of the chosen token and map it
        through exp(). This is a proxy, not a calibrated probability: it tells
        you reliably which lines the model was least sure about, which is
        exactly what the review queue needs, but the absolute value should not
        be quoted as an accuracy figure.
        """
        import torch

        scores = getattr(generated, "scores", None)
        sequences = generated.sequences
        if not scores:
            return [0.5] * len(sequences)

        # sequences includes the decoder start token, scores do not.
        tokens = sequences[:, 1:]
        n_steps = min(len(scores), tokens.shape[1])

        # Generation pads every sequence in a batch out to the longest one. Those
        # padding steps are not predictions, and their probability is ~0, so
        # averaging over them punishes a line for the length of its neighbours:
        # a short, perfectly-read line batched with a long one scored 0.01 while
        # a misread line scored 0.90. That is worse than no signal at all -- the
        # review queue sorts by this, so it was showing reviewers the good lines
        # and hiding the bad ones. Stop at end-of-sequence.
        eos_id, pad_id = self._special_token_ids()

        out: list[float] = []
        for row in range(tokens.shape[0]):
            logprobs = []
            for step in range(n_steps):
                token_id = tokens[row, step].item()
                # Padding only appears once the sequence has already ended.
                if pad_id is not None and token_id == pad_id and token_id != eos_id:
                    break
                step_logits = scores[step][row].float()
                lp = torch.log_softmax(step_logits, dim=-1)[token_id].item()
                if math.isfinite(lp):
                    logprobs.append(lp)
                # EOS is a real prediction, so it counts -- but nothing after it does.
                if eos_id is not None and token_id == eos_id:
                    break
            out.append(float(math.exp(sum(logprobs) / len(logprobs))) if logprobs else 0.5)
        return out

    @staticmethod
    def _split_into_words(text: str, line_box: BBox, confidence: float) -> list[Word]:
        """Distribute the line box across whitespace-separated tokens.

        Widths are apportioned by character count including the separating
        space, which is a decent approximation for a single line of text and
        costs nothing. These boxes are estimates, not measurements.
        """
        tokens = [t for t in text.split() if t]
        if not tokens:
            return []

        total_chars = sum(len(t) for t in tokens) + (len(tokens) - 1)
        if total_chars <= 0:
            return []

        words: list[Word] = []
        cursor = line_box.x
        for i, token in enumerate(tokens):
            share = len(token) / total_chars
            width = max(1, int(round(line_box.w * share)))
            words.append(
                Word(
                    text=token,
                    bbox=BBox(cursor, line_box.y, width, line_box.h),
                    confidence=confidence,
                    engine="trocr(approx-boxes)",
                )
            )
            space = int(round(line_box.w / total_chars)) if i < len(tokens) - 1 else 0
            cursor += width + space
        return words
