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

        from PIL import Image

        lines: list[OcrLine] = []
        for img_bytes in images:
            img = Image.open(BytesIO(img_bytes)).convert("RGB")
            result = self._ocr.ocr(img, cls=True)
            # result: list[list[[box, (text, conf)]]]
            for block in result or []:
                for _box, (text, conf) in block:
                    if text:
                        lines.append(OcrLine(text=str(text), confidence=float(conf) if conf is not None else None))
        return lines

