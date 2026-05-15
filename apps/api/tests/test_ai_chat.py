from collections.abc import AsyncIterator

import pytest
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.routes import ai
from app.domain.ai.fastgpt_client import (
    FastGPTConfigError,
    FastGPTUpstreamError,
    parse_fastgpt_sse_line,
    stream_fastgpt_response,
)
from app.domain.ai.models import ChatMessage
from app.settings import Settings


async def consume_stream(stream):
    return [chunk async for chunk in stream]


async def fake_stream_response(*args, **kwargs) -> AsyncIterator[str]:
    yield "第一段"
    yield "第二段"


async def fake_config_error(*args, **kwargs) -> AsyncIterator[str]:
    raise ai.FastGPTConfigError("missing key")
    yield ""


def test_chat_endpoint_streams_normalized_sse(monkeypatch):
    monkeypatch.setattr(ai, "stream_fastgpt_response", fake_stream_response)
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/ai/chat",
        json={"messages": [{"role": "user", "content": "今日推荐"}]},
    ) as response:
        body = response.read().decode("utf-8")

    assert response.status_code == 200
    assert "event: chunk" in body
    assert 'data: {"content":"第一段"}' in body
    assert 'data: {"content":"第二段"}' in body
    assert "event: done" in body


def test_chat_endpoint_returns_config_error(monkeypatch):
    monkeypatch.setattr(ai, "stream_fastgpt_response", fake_config_error)
    client = TestClient(app)

    with client.stream(
        "POST",
        "/api/ai/chat",
        json={"messages": [{"role": "user", "content": "今日推荐"}]},
    ) as response:
        body = response.read().decode("utf-8")

    assert response.status_code == 200
    assert "event: error" in body
    assert "AI 服务未配置" in body
    assert "FASTGPT_API_KEY" not in body


def test_parse_openai_style_delta_content():
    line = 'data: {"choices":[{"delta":{"content":"你好"}}]}'

    assert parse_fastgpt_sse_line(line) == "你好"


def test_parse_openai_style_message_content():
    line = 'data: {"choices":[{"message":{"content":"完整回答"}}]}'

    assert parse_fastgpt_sse_line(line) == "完整回答"


def test_parse_plain_text_data_line():
    line = "data: 普通文本"

    assert parse_fastgpt_sse_line(line) == "普通文本"


def test_parse_done_line_returns_none():
    assert parse_fastgpt_sse_line("data: [DONE]") is None


def test_parse_blank_line_returns_none():
    assert parse_fastgpt_sse_line("") is None


@pytest.mark.parametrize("line", ["event: ping", "id: abc", "retry: 1000", ": keepalive"])
def test_parse_sse_metadata_lines_returns_none(line):
    assert parse_fastgpt_sse_line(line) is None


@pytest.mark.parametrize("line", ["data: [1,2]", "data: 123"])
def test_parse_non_dict_json_payloads_return_none(line):
    assert parse_fastgpt_sse_line(line) is None


def test_parse_json_string_payload_returns_string():
    assert parse_fastgpt_sse_line('data: "hello"') == "hello"


async def test_stream_fastgpt_response_yields_empty_string_chunks(monkeypatch):
    class FakeResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def aiter_lines(self):
            yield 'data: {"choices":[{"delta":{"content":""}}]}'
            yield 'data: {"choices":[{"delta":{"content":"after"}}]}'

    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        def stream(self, method, url, headers, json):
            return FakeResponse()

    monkeypatch.setattr("app.domain.ai.fastgpt_client.httpx.AsyncClient", FakeAsyncClient)

    settings = Settings(fastgpt_api_key="test-key")
    messages = [ChatMessage(role="user", content="hi")]

    chunks = await consume_stream(stream_fastgpt_response(settings, messages))

    assert chunks == ["", "after"]


async def test_stream_fastgpt_response_wraps_httpx_errors(monkeypatch):
    class FakeAsyncClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        def stream(self, method, url, headers, json):
            raise httpx.ConnectError("connection failed")

    monkeypatch.setattr("app.domain.ai.fastgpt_client.httpx.AsyncClient", FakeAsyncClient)

    settings = Settings(fastgpt_api_key="test-key")
    messages = [ChatMessage(role="user", content="hi")]

    with pytest.raises(FastGPTUpstreamError, match="FastGPT upstream request failed"):
        await consume_stream(stream_fastgpt_response(settings, messages))


async def test_stream_fastgpt_response_missing_api_key_raises_config_error():
    settings = Settings(fastgpt_api_key=None)
    messages = [ChatMessage(role="user", content="hi")]

    with pytest.raises(FastGPTConfigError, match="FASTGPT_API_KEY is not configured"):
        await consume_stream(stream_fastgpt_response(settings, messages))
