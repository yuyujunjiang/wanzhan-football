from __future__ import annotations

from app.settings import settings

from .ocr_service import OcrService, StubOcrService


_singletons: dict[str, OcrService] = {}


def get_ocr_service(*, provider: str | None = None) -> OcrService:
    provider = (provider or settings.ocr_provider or "stub").lower()
    if provider in _singletons:
        return _singletons[provider]
    if provider == "stub":
        svc = StubOcrService()
        _singletons[provider] = svc
        return svc
    if provider == "paddle":
        from .paddleocr_impl import PaddleOcrService

        svc = PaddleOcrService()
        _singletons[provider] = svc
        return svc
    raise ValueError(f"Unknown OCR provider: {provider!r}")

