from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class OcrLine:
    text: str
    confidence: float | None = None


class OcrService(Protocol):
    def recognize(self, *, images: list[bytes], source_images: list[str]) -> list[OcrLine]: ...


class StubOcrService:
    def recognize(self, *, images: list[bytes], source_images: list[str]) -> list[OcrLine]:
        # Deterministic stub output for MVP wiring & tests.
        return [
            OcrLine("竞彩足球 SPF"),
            OcrLine("倍投 2"),
            OcrLine("过关方式 2x1"),
            OcrLine("2026-05-08 EPL A vs B 胜 1.85"),
            OcrLine("2026-05-08 EPL C vs D 平 2.10"),
        ]
