from collections.abc import AsyncIterator
import json

import httpx

from app.domain.ai.models import ChatMessage
from app.settings import Settings


class FastGPTConfigError(RuntimeError):
    pass


class FastGPTUpstreamError(RuntimeError):
    pass


def parse_fastgpt_sse_line(line: str) -> str | None:
    stripped = line.strip()
    if not stripped:
        return None
    if stripped.startswith(":") or stripped.startswith(("event:", "id:", "retry:")):
        return None
    if stripped.startswith("data:"):
        stripped = stripped.removeprefix("data:").strip()
    if stripped == "[DONE]":
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return stripped

    if isinstance(payload, str):
        return payload
    if not isinstance(payload, dict):
        return None

    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            delta = first.get("delta")
            if isinstance(delta, dict) and isinstance(delta.get("content"), str):
                return delta["content"]
            message = first.get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"]

    if isinstance(payload.get("content"), str):
        return payload["content"]
    if isinstance(payload.get("text"), str):
        return payload["text"]
    return None


def build_fastgpt_payload(messages: list[ChatMessage]) -> dict:
    return {
        "stream": True,
        "messages": [{"role": message.role, "content": message.content} for message in messages],
    }


async def stream_fastgpt_response(
    settings: Settings,
    messages: list[ChatMessage],
) -> AsyncIterator[str]:
    if not settings.fastgpt_api_key:
        raise FastGPTConfigError("FASTGPT_API_KEY is not configured")

    headers = {
        "Authorization": f"Bearer {settings.fastgpt_api_key}",
        "Content-Type": "application/json",
    }
    timeout = httpx.Timeout(settings.fastgpt_timeout_seconds)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                settings.fastgpt_chat_url,
                headers=headers,
                json=build_fastgpt_payload(messages),
            ) as response:
                if response.status_code >= 400:
                    await response.aread()
                    raise FastGPTUpstreamError(f"FastGPT upstream returned {response.status_code}")

                async for line in response.aiter_lines():
                    chunk = parse_fastgpt_sse_line(line)
                    if chunk is not None:
                        yield chunk
    except httpx.HTTPError as exc:
        raise FastGPTUpstreamError("FastGPT upstream request failed") from exc
