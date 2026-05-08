from __future__ import annotations

from typing import TYPE_CHECKING

from .ocr_service import OcrLine

if TYPE_CHECKING:
    from paddleocr import PaddleOCR


class PaddleOcrService:
    """
    Real OCR implementation using PaddleOCR.

    Note: PaddleOCR + paddlepaddle can be heavy and may require platform-specific wheels.
    We keep this implementation isolated and lazy-imported by factory to avoid breaking dev/test
    environments that don't have the dependency installed yet.
    """

    def __init__(self) -> None:
        from paddleocr import PaddleOCR  # lazy import

        # MVP defaults: Chinese + angle classification improves receipt/ticket photos.
        self._ocr: PaddleOCR = PaddleOCR(use_angle_cls=True, lang="ch")

    def recognize(self, *, images: list[bytes], source_images: list[str]) -> list[OcrLine]:
        # PaddleOCR accepts numpy arrays / image paths; we pass bytes by decoding via PIL.
        from io import BytesIO

        import numpy as np
        from PIL import Image

        lines: list[OcrLine] = []
        for img_bytes in images:
            pil = Image.open(BytesIO(img_bytes)).convert("RGB")
            img = np.array(pil)
            # paddleocr>=3.5: `use_angle_cls` is configured at init; `cls` kw is not accepted.
            result = self._ocr.ocr(img)
            # Result shape differs across paddleocr major versions:
            # - older: list[list[[box, (text, conf)]]]
            # - newer (>=3.5): list[OCRResult], where OCRResult behaves like a dict with `rec_texts`/`rec_scores`
            for page in result or []:
                # Newer: dict-like OCRResult
                try:
                    rec_texts = page.get("rec_texts")  # type: ignore[attr-defined]
                    rec_scores = page.get("rec_scores")  # type: ignore[attr-defined]
                except Exception:
                    rec_texts = None
                    rec_scores = None

                if isinstance(rec_texts, list) and rec_texts:
                    for i, text in enumerate(rec_texts):
                        if not text:
                            continue
                        conf = None
                        if isinstance(rec_scores, list) and i < len(rec_scores):
                            try:
                                conf = float(rec_scores[i])
                            except Exception:
                                conf = None
                        lines.append(OcrLine(text=str(text), confidence=conf))
                    continue

                # Fallback older shape
                if isinstance(page, list):
                    for block in page:
                        if not isinstance(block, list):
                            continue
                        for item in block:
                            if not (isinstance(item, (list, tuple)) and len(item) == 2):
                                continue
                            _box, tc = item
                            if not (isinstance(tc, (list, tuple)) and len(tc) == 2):
                                continue
                            text, conf = tc
                            if text:
                                lines.append(
                                    OcrLine(
                                        text=str(text),
                                        confidence=float(conf) if conf is not None else None,
                                    )
                                )
        return lines

