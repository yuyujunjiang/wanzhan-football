from __future__ import annotations

from app.settings import settings

from .ocr_service import OcrService, StubOcrService


def get_ocr_service() -> OcrService:
    provider = (settings.ocr_provider or "stub").lower()
    if provider == "stub":
        return StubOcrService()
    if provider == "paddle":
        from .paddleocr_impl import PaddleOcrService

        return PaddleOcrService()
    raise ValueError(f"Unknown OCR provider: {settings.ocr_provider!r}")

