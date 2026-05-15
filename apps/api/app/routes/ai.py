from collections.abc import AsyncIterator
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.domain.ai.fastgpt_client import (
    FastGPTConfigError,
    FastGPTUpstreamError,
    stream_fastgpt_response,
)
from app.domain.ai.models import ChatRequest
from app.settings import settings


router = APIRouter(prefix="/api/ai", tags=["ai"])


def sse_event(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"


async def chat_event_stream(request: ChatRequest) -> AsyncIterator[str]:
    try:
        async for chunk in stream_fastgpt_response(settings, request.messages):
            yield sse_event("chunk", {"content": chunk})
        yield sse_event("done", {})
    except FastGPTConfigError:
        yield sse_event("error", {"message": "AI 服务未配置"})
    except FastGPTUpstreamError:
        yield sse_event("error", {"message": "AI 服务暂时不可用，请稍后重试"})
    except Exception:
        yield sse_event("error", {"message": "回答中断，可重试"})


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    return StreamingResponse(
        chat_event_stream(request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
