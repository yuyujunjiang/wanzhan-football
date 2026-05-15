# AI Data Chat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `AI数据` Tab as a mobile-first white/gray full-screen streaming chat page backed by a FastGPT proxy.

**Architecture:** Use a small Next.js frontend in `apps/web` and a FastAPI backend in `apps/api`. The frontend renders the chat UI and consumes a streaming `/api/ai/chat` endpoint; the backend owns FastGPT configuration, authorization, timeout handling, and stream normalization so the browser never receives the API key.

**Tech Stack:** Next.js App Router, React, TypeScript, CSS Modules, FastAPI, Pydantic Settings, httpx async streaming, pytest, FastAPI TestClient.

---

## Scope Check

This plan implements only the approved chat-only scope:

- Full-screen `AI数据` chat page.
- White/gray visual style.
- Three fixed prompt chips with `今日推荐` first.
- Streaming FastGPT response through backend proxy.
- Stop generation, retry, and readable error states.
- Configuration through `.env` / `.env.example`.

This plan does not implement:

- Stock-style dashboards.
- Match crawlers, odds trends, or data cleaning.
- Persistent chat history.
- Global floating AI assistant.
- Ticket detail context injection.

## Target File Structure

### Backend: `apps/api`

- Create: `apps/api/pyproject.toml` — Python dependencies and pytest config.
- Create: `apps/api/.env.example` — safe configuration template.
- Create: `apps/api/app/__init__.py` — package marker.
- Create: `apps/api/app/main.py` — FastAPI app wiring, CORS, health route, AI router.
- Create: `apps/api/app/settings.py` — environment settings for FastGPT and CORS.
- Create: `apps/api/app/routes/__init__.py` — routes package marker.
- Create: `apps/api/app/routes/ai.py` — `/api/ai/chat` streaming endpoint.
- Create: `apps/api/app/domain/__init__.py` — domain package marker.
- Create: `apps/api/app/domain/ai/__init__.py` — AI package marker.
- Create: `apps/api/app/domain/ai/models.py` — Pydantic request/message models.
- Create: `apps/api/app/domain/ai/fastgpt_client.py` — upstream FastGPT streaming client and stream parser.
- Create: `apps/api/tests/test_ai_chat.py` — API tests for config, streaming, and errors.
- Create: `apps/api/tests/test_health.py` — health test.

### Frontend: `apps/web`

- Create: `apps/web/package.json` — Next scripts and dependencies.
- Create: `apps/web/tsconfig.json` — TypeScript config.
- Create: `apps/web/next.config.mjs` — Next config.
- Create: `apps/web/src/app/layout.tsx` — root app layout.
- Create: `apps/web/src/app/page.tsx` — redirect/link landing to `AI数据`.
- Create: `apps/web/src/app/ai/page.tsx` — AI data chat tab page.
- Create: `apps/web/src/app/globals.css` — global reset and body styling.
- Create: `apps/web/src/components/ai/ChatPage.tsx` — chat page client component.
- Create: `apps/web/src/components/ai/ChatPage.module.css` — white/gray chat UI styles.
- Create: `apps/web/src/lib/aiChatStream.ts` — streaming fetch client and SSE parser.
- Create: `apps/web/src/lib/aiChatStream.test.ts` — unit tests for frontend stream parsing.
- Create: `apps/web/src/test/setup.ts` — Vitest setup.
- Create: `apps/web/vitest.config.ts` — test config.

## Local Commands

- API install/test:

```bash
cd apps/api
uv sync --extra dev
uv run pytest -q
```

- API dev server:

```bash
cd apps/api
uv run uvicorn app.main:app --reload --port 8000
```

- Web install/test/build/dev:

```bash
cd apps/web
npm install
npm test
npm run build
npm run dev
```

---

### Task 1: Bootstrap FastAPI App and Settings

**Files:**
- Create: `apps/api/pyproject.toml`
- Create: `apps/api/.env.example`
- Create: `apps/api/app/__init__.py`
- Create: `apps/api/app/main.py`
- Create: `apps/api/app/settings.py`
- Create: `apps/api/app/routes/__init__.py`
- Create: `apps/api/tests/test_health.py`

- [ ] **Step 1: Write the failing health test**

Create `apps/api/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_ok():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True}
```

- [ ] **Step 2: Add backend dependencies**

Create `apps/api/pyproject.toml`:

```toml
[project]
name = "football-calculator-api"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115.0",
  "httpx>=0.27.0",
  "pydantic>=2.7.0",
  "pydantic-settings>=2.3.0",
  "uvicorn[standard]>=0.32.0"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
  "pytest-asyncio>=0.23.0",
  "ruff>=0.5.0"
]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
```

- [ ] **Step 3: Add safe environment template**

Create `apps/api/.env.example`:

```bash
FASTGPT_API_BASE=http://175.27.228.129:4000/api
FASTGPT_API_KEY=replace-with-your-fastgpt-key
FASTGPT_CHAT_PATH=/v1/chat/completions
FASTGPT_TIMEOUT_SECONDS=30
WEB_ORIGIN=http://localhost:3000
```

- [ ] **Step 4: Add settings**

Create `apps/api/app/settings.py`:

```python
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    fastgpt_api_base: str = Field(default="http://175.27.228.129:4000/api")
    fastgpt_api_key: str | None = Field(default=None)
    fastgpt_chat_path: str = Field(default="/v1/chat/completions")
    fastgpt_timeout_seconds: float = Field(default=30)
    web_origin: str = Field(default="http://localhost:3000")

    @property
    def fastgpt_chat_url(self) -> str:
        base = self.fastgpt_api_base.rstrip("/")
        path = self.fastgpt_chat_path if self.fastgpt_chat_path.startswith("/") else f"/{self.fastgpt_chat_path}"
        return f"{base}{path}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 5: Add app package markers**

Create empty package marker files:

```python
# apps/api/app/__init__.py
```

```python
# apps/api/app/routes/__init__.py
```

- [ ] **Step 6: Add FastAPI app with health route**

Create `apps/api/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.settings import get_settings


settings = get_settings()

app = FastAPI(title="Football Calculator API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}
```

- [ ] **Step 7: Run backend tests**

Run:

```bash
cd apps/api
uv sync --extra dev
uv run pytest -q
```

Expected: `1 passed`.

- [ ] **Step 8: Commit backend bootstrap**

```bash
git add apps/api
git commit -m "chore: bootstrap FastAPI chat backend"
```

---

### Task 2: Implement FastGPT Stream Adapter

**Files:**
- Create: `apps/api/app/domain/__init__.py`
- Create: `apps/api/app/domain/ai/__init__.py`
- Create: `apps/api/app/domain/ai/models.py`
- Create: `apps/api/app/domain/ai/fastgpt_client.py`
- Create: `apps/api/tests/test_ai_chat.py`

- [ ] **Step 1: Write stream parser tests first**

Create `apps/api/tests/test_ai_chat.py`:

```python
import pytest

from app.domain.ai.fastgpt_client import parse_fastgpt_sse_line


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
```

- [ ] **Step 2: Add AI request models**

Create package markers:

```python
# apps/api/app/domain/__init__.py
```

```python
# apps/api/app/domain/ai/__init__.py
```

Create `apps/api/app/domain/ai/models.py`:

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ChatRole = Literal["system", "user", "assistant"]


class ChatMessage(BaseModel):
    role: ChatRole
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessage] = Field(min_length=1, max_length=40)
```

- [ ] **Step 3: Implement FastGPT parser and stream client**

Create `apps/api/app/domain/ai/fastgpt_client.py`:

```python
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
    if stripped.startswith("data:"):
        stripped = stripped.removeprefix("data:").strip()
    if stripped == "[DONE]":
        return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return stripped

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
                if chunk:
                    yield chunk
```

- [ ] **Step 4: Run parser tests**

Run:

```bash
cd apps/api
uv run pytest tests/test_ai_chat.py -q
```

Expected: `5 passed`.

- [ ] **Step 5: Commit stream adapter**

```bash
git add apps/api/app/domain apps/api/tests/test_ai_chat.py
git commit -m "feat: add FastGPT stream adapter"
```

---

### Task 3: Implement `/api/ai/chat` Streaming Endpoint

**Files:**
- Modify: `apps/api/app/routes/ai.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/tests/test_ai_chat.py`

- [ ] **Step 1: Add endpoint tests**

Append to `apps/api/tests/test_ai_chat.py`:

```python
from collections.abc import AsyncIterator

from fastapi.testclient import TestClient

from app.main import app
from app.routes import ai


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
```

- [ ] **Step 2: Implement route**

Create `apps/api/app/routes/ai.py`:

```python
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
from app.settings import get_settings

router = APIRouter(prefix="/api/ai", tags=["ai"])


def sse_event(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n\n"


async def chat_event_stream(request: ChatRequest) -> AsyncIterator[str]:
    try:
        async for chunk in stream_fastgpt_response(get_settings(), request.messages):
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
```

- [ ] **Step 3: Register AI router**

Modify `apps/api/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.ai import router as ai_router
from app.settings import get_settings


settings = get_settings()

app = FastAPI(title="Football Calculator API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.web_origin],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(ai_router)


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}
```

- [ ] **Step 4: Run endpoint tests**

Run:

```bash
cd apps/api
uv run pytest tests/test_ai_chat.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit streaming endpoint**

```bash
git add apps/api/app/routes/ai.py apps/api/app/main.py apps/api/tests/test_ai_chat.py
git commit -m "feat: add streaming AI chat endpoint"
```

---

### Task 4: Bootstrap Next.js Web App

**Files:**
- Create: `apps/web/package.json`
- Create: `apps/web/tsconfig.json`
- Create: `apps/web/next.config.mjs`
- Create: `apps/web/src/app/layout.tsx`
- Create: `apps/web/src/app/page.tsx`
- Create: `apps/web/src/app/globals.css`

- [ ] **Step 1: Add web package**

Create `apps/web/package.json`:

```json
{
  "name": "football-calculator-web",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build",
    "start": "next start -p 3000",
    "test": "vitest run"
  },
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@testing-library/react": "^16.0.0",
    "@testing-library/user-event": "^14.5.0",
    "@types/node": "^22.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "jsdom": "^25.0.0",
    "typescript": "^5.6.0",
    "vitest": "^2.1.0"
  }
}
```

- [ ] **Step 2: Add TypeScript and Next config**

Create `apps/web/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }]
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

Create `apps/web/next.config.mjs`:

```js
/** @type {import('next').NextConfig} */
const nextConfig = {};

export default nextConfig;
```

- [ ] **Step 3: Add global layout**

Create `apps/web/src/app/globals.css`:

```css
* {
  box-sizing: border-box;
}

html,
body {
  margin: 0;
  min-height: 100%;
  background: #f3f4f6;
  color: #111827;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

button,
input,
textarea {
  font: inherit;
}
```

Create `apps/web/src/app/layout.tsx`:

```tsx
import "./globals.css";

export const metadata = {
  title: "足球计算器",
  description: "AI 数据聊天页"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
```

- [ ] **Step 4: Add landing page link to AI tab**

Create `apps/web/src/app/page.tsx`:

```tsx
import Link from "next/link";

export default function HomePage() {
  return (
    <main style={{ minHeight: "100dvh", padding: 24 }}>
      <h1>足球计算器</h1>
      <p>进入 AI 数据页，与 FastGPT 知识库对话。</p>
      <Link href="/ai">打开 AI数据</Link>
    </main>
  );
}
```

- [ ] **Step 5: Install and build**

Run:

```bash
cd apps/web
npm install
npm run build
```

Expected: Next build completes successfully.

- [ ] **Step 6: Commit web bootstrap**

```bash
git add apps/web
git commit -m "chore: bootstrap Next.js web app"
```

---

### Task 5: Implement Frontend Stream Client

**Files:**
- Create: `apps/web/src/lib/aiChatStream.ts`
- Create: `apps/web/src/lib/aiChatStream.test.ts`
- Create: `apps/web/src/test/setup.ts`
- Create: `apps/web/vitest.config.ts`

- [ ] **Step 1: Add stream parser tests**

Create `apps/web/src/lib/aiChatStream.test.ts`:

```ts
import { describe, expect, it } from "vitest";

import { parseSseBlock } from "./aiChatStream";

describe("parseSseBlock", () => {
  it("parses chunk events", () => {
    expect(parseSseBlock('event: chunk\ndata: {"content":"你好"}')).toEqual({
      event: "chunk",
      data: { content: "你好" }
    });
  });

  it("parses done events", () => {
    expect(parseSseBlock("event: done\ndata: {}")).toEqual({
      event: "done",
      data: {}
    });
  });

  it("parses error events", () => {
    expect(parseSseBlock('event: error\ndata: {"message":"AI 服务未配置"}')).toEqual({
      event: "error",
      data: { message: "AI 服务未配置" }
    });
  });
});
```

- [ ] **Step 2: Add Vitest config**

Create `apps/web/vitest.config.ts`:

```ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"]
  }
});
```

Create `apps/web/src/test/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

Add the missing testing dependency to `apps/web/package.json`:

```json
"@testing-library/jest-dom": "^6.6.0"
```

- [ ] **Step 3: Implement streaming client helpers**

Create `apps/web/src/lib/aiChatStream.ts`:

```ts
export type ChatRole = "user" | "assistant" | "system";

export type ChatMessagePayload = {
  role: ChatRole;
  content: string;
};

export type ParsedSseEvent = {
  event: string;
  data: Record<string, unknown>;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function parseSseBlock(block: string): ParsedSseEvent {
  const eventLine = block.split("\n").find((line) => line.startsWith("event:"));
  const dataLine = block.split("\n").find((line) => line.startsWith("data:"));

  const event = eventLine?.replace("event:", "").trim() ?? "message";
  const rawData = dataLine?.replace("data:", "").trim() ?? "{}";

  return {
    event,
    data: JSON.parse(rawData) as Record<string, unknown>
  };
}

export async function streamAiChat(params: {
  messages: ChatMessagePayload[];
  signal: AbortSignal;
  onChunk: (content: string) => void;
  onDone: () => void;
  onError: (message: string) => void;
}): Promise<void> {
  const response = await fetch(`${API_BASE}/api/ai/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages: params.messages }),
    signal: params.signal
  });

  if (!response.ok || !response.body) {
    params.onError("AI 服务暂时不可用，请稍后重试");
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      if (!block.trim()) continue;
      const parsed = parseSseBlock(block);
      if (parsed.event === "chunk" && typeof parsed.data.content === "string") {
        params.onChunk(parsed.data.content);
      }
      if (parsed.event === "done") {
        params.onDone();
      }
      if (parsed.event === "error") {
        params.onError(
          typeof parsed.data.message === "string"
            ? parsed.data.message
            : "回答中断，可重试"
        );
      }
    }
  }
}
```

- [ ] **Step 4: Run frontend parser tests**

Run:

```bash
cd apps/web
npm install
npm test -- src/lib/aiChatStream.test.ts
```

Expected: parser tests pass.

- [ ] **Step 5: Commit stream client**

```bash
git add apps/web/src/lib apps/web/src/test apps/web/vitest.config.ts apps/web/package.json
git commit -m "feat: add AI chat stream client"
```

---

### Task 6: Build AI Data Chat Page UI

**Files:**
- Create: `apps/web/src/app/ai/page.tsx`
- Create: `apps/web/src/components/ai/ChatPage.tsx`
- Create: `apps/web/src/components/ai/ChatPage.module.css`

- [ ] **Step 1: Implement AI route**

Create `apps/web/src/app/ai/page.tsx`:

```tsx
import { ChatPage } from "../../components/ai/ChatPage";

export default function AiPage() {
  return <ChatPage />;
}
```

- [ ] **Step 2: Implement chat page component**

Create `apps/web/src/components/ai/ChatPage.tsx`:

```tsx
"use client";

import { useRef, useState } from "react";

import { streamAiChat, type ChatMessagePayload } from "../../lib/aiChatStream";
import styles from "./ChatPage.module.css";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: "streaming" | "done" | "error" | "stopped";
};

const PROMPTS = ["今日推荐", "帮我复盘这张票哪里判断错了", "解释一下让球胜平负怎么理解"];

function createId(): string {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [connectionLabel, setConnectionLabel] = useState("已连接");
  const activeRequest = useRef<AbortController | null>(null);

  async function sendMessage(text: string) {
    const content = text.trim();
    if (!content || isStreaming) return;

    const userMessage: Message = { id: createId(), role: "user", content };
    const assistantId = createId();
    const assistantMessage: Message = {
      id: assistantId,
      role: "assistant",
      content: "正在思考...",
      status: "streaming"
    };

    const nextMessages = [...messages, userMessage, assistantMessage];
    setMessages(nextMessages);
    setInputValue("");
    setIsStreaming(true);
    setConnectionLabel("连接中");

    const controller = new AbortController();
    activeRequest.current = controller;

    const payloadMessages: ChatMessagePayload[] = [...messages, userMessage].map((message) => ({
      role: message.role,
      content: message.content
    }));

    let receivedAnyChunk = false;

    try {
      await streamAiChat({
        messages: payloadMessages,
        signal: controller.signal,
        onChunk: (chunk) => {
          receivedAnyChunk = true;
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? {
                    ...message,
                    content:
                      message.content === "正在思考..." ? chunk : `${message.content}${chunk}`,
                    status: "streaming"
                  }
                : message
            )
          );
        },
        onDone: () => {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId ? { ...message, status: "done" } : message
            )
          );
        },
        onError: (messageText) => {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? {
                    ...message,
                    content: receivedAnyChunk
                      ? `${message.content}\n\n${messageText}`
                      : messageText,
                    status: "error"
                  }
                : message
            )
          );
          setConnectionLabel(messageText === "AI 服务未配置" ? "未配置" : "不可用");
        }
      });
    } catch (error) {
      if (controller.signal.aborted) {
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantId
              ? {
                  ...message,
                  content: message.content === "正在思考..." ? "已停止" : message.content,
                  status: "stopped"
                }
              : message
          )
        );
      } else {
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantId
              ? { ...message, content: "回答中断，可重试", status: "error" }
              : message
          )
        );
        setConnectionLabel("不可用");
      }
    } finally {
      setIsStreaming(false);
      activeRequest.current = null;
      setConnectionLabel((current) => (current === "连接中" ? "已连接" : current));
    }
  }

  function stopStreaming() {
    activeRequest.current?.abort();
  }

  function retryLastUserMessage() {
    const lastUserMessage = [...messages].reverse().find((message) => message.role === "user");
    if (lastUserMessage) {
      void sendMessage(lastUserMessage.content);
    }
  }

  return (
    <main className={styles.page}>
      <header className={styles.header}>
        <h1>AI数据</h1>
        <span className={styles.status}>{connectionLabel}</span>
      </header>

      <section className={styles.messages} aria-label="聊天记录">
        {messages.length === 0 ? (
          <>
            <div className={styles.welcome}>
              <h2>想分析什么？</h2>
              <p>可以问比赛判断、票据复盘、玩法解释或投注记录里的模式。</p>
            </div>
            <div className={styles.prompts}>
              {PROMPTS.map((prompt, index) => (
                <button
                  className={index === 0 ? styles.primaryPrompt : styles.prompt}
                  key={prompt}
                  onClick={() => void sendMessage(prompt)}
                  type="button"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </>
        ) : (
          messages.map((message) => (
            <article
              className={`${styles.bubble} ${
                message.role === "user" ? styles.userBubble : styles.assistantBubble
              }`}
              key={message.id}
            >
              <p>{message.content}</p>
              {message.status === "error" ? (
                <button className={styles.retry} onClick={retryLastUserMessage} type="button">
                  重试
                </button>
              ) : null}
              {message.status === "stopped" ? <small>已停止</small> : null}
            </article>
          ))
        )}
      </section>

      <form
        className={styles.composer}
        onSubmit={(event) => {
          event.preventDefault();
          void sendMessage(inputValue);
        }}
      >
        <input
          aria-label="输入问题"
          disabled={isStreaming}
          onChange={(event) => setInputValue(event.target.value)}
          placeholder="输入问题..."
          value={inputValue}
        />
        {isStreaming ? (
          <button onClick={stopStreaming} type="button">
            停止
          </button>
        ) : (
          <button disabled={!inputValue.trim()} type="submit">
            发送
          </button>
        )}
      </form>
    </main>
  );
}
```

- [ ] **Step 3: Implement white/gray mobile-first styles**

Create `apps/web/src/components/ai/ChatPage.module.css`:

```css
.page {
  min-height: 100dvh;
  background: #f3f4f6;
  color: #111827;
  display: flex;
  flex-direction: column;
  max-width: 720px;
  margin: 0 auto;
  border-left: 1px solid #e5e7eb;
  border-right: 1px solid #e5e7eb;
}

.header {
  height: 58px;
  padding: 0 16px;
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 800;
}

.status {
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  color: #4b5563;
  background: #f9fafb;
  padding: 5px 10px;
  font-size: 12px;
}

.messages {
  flex: 1;
  padding: 16px 14px 96px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
}

.welcome,
.assistantBubble,
.prompt,
.primaryPrompt {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  box-shadow: 0 8px 22px rgba(17, 24, 39, 0.04);
}

.welcome {
  border-radius: 10px;
  padding: 16px;
}

.welcome h2 {
  margin: 0 0 8px;
  font-size: 20px;
}

.welcome p {
  margin: 0;
  color: #6b7280;
  line-height: 1.5;
}

.prompts {
  display: grid;
  gap: 8px;
}

.prompt,
.primaryPrompt {
  min-height: 42px;
  border-radius: 8px;
  color: #1f2937;
  text-align: left;
  padding: 0 12px;
}

.primaryPrompt {
  background: #eef1f5;
  border-color: #d1d5db;
  font-weight: 700;
}

.bubble {
  max-width: min(82%, 560px);
  border-radius: 12px;
  padding: 11px 12px;
  line-height: 1.55;
  white-space: pre-wrap;
}

.bubble p {
  margin: 0;
}

.assistantBubble {
  align-self: flex-start;
}

.userBubble {
  align-self: flex-end;
  background: #111827;
  color: #ffffff;
}

.retry {
  margin-top: 8px;
  border: 1px solid #d1d5db;
  background: #f9fafb;
  color: #111827;
  border-radius: 8px;
  padding: 6px 10px;
}

.composer {
  position: fixed;
  left: 50%;
  bottom: 0;
  width: min(100%, 720px);
  transform: translateX(-50%);
  background: rgba(255, 255, 255, 0.94);
  border-top: 1px solid #e5e7eb;
  padding: 10px;
  display: flex;
  gap: 8px;
}

.composer input {
  min-width: 0;
  flex: 1;
  min-height: 44px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #f3f4f6;
  padding: 0 14px;
  color: #111827;
}

.composer button {
  min-width: 64px;
  min-height: 44px;
  border: 0;
  border-radius: 999px;
  background: #111827;
  color: #ffffff;
  font-weight: 700;
}

.composer button:disabled {
  background: #d1d5db;
  color: #6b7280;
}
```

- [ ] **Step 4: Build web app**

Run:

```bash
cd apps/web
npm run build
```

Expected: build succeeds.

- [ ] **Step 5: Commit chat UI**

```bash
git add apps/web/src/app/ai apps/web/src/components/ai apps/web/src/app/page.tsx
git commit -m "feat: build AI data chat page"
```

---

### Task 7: Add Frontend Interaction Tests

**Files:**
- Create: `apps/web/src/components/ai/ChatPage.test.tsx`

- [ ] **Step 1: Write UI tests**

Create `apps/web/src/components/ai/ChatPage.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ChatPage } from "./ChatPage";

vi.mock("../../lib/aiChatStream", () => ({
  streamAiChat: vi.fn(async ({ onChunk, onDone }) => {
    onChunk("流式");
    onChunk("回答");
    onDone();
  })
}));

describe("ChatPage", () => {
  it("shows prompt chips with 今日推荐 first", () => {
    render(<ChatPage />);

    const buttons = screen.getAllByRole("button");
    expect(buttons[0]).toHaveTextContent("今日推荐");
  });

  it("sends a prompt and appends streamed answer", async () => {
    const user = userEvent.setup();
    render(<ChatPage />);

    await user.click(screen.getByRole("button", { name: "今日推荐" }));

    expect(await screen.findByText("今日推荐")).toBeInTheDocument();
    expect(await screen.findByText("流式回答")).toBeInTheDocument();
  });

  it("does not send blank input", async () => {
    render(<ChatPage />);

    expect(screen.getByRole("button", { name: "发送" })).toBeDisabled();
  });
});
```

- [ ] **Step 2: Run frontend tests**

Run:

```bash
cd apps/web
npm test
```

Expected: all tests pass.

- [ ] **Step 3: Commit UI tests**

```bash
git add apps/web/src/components/ai/ChatPage.test.tsx
git commit -m "test: cover AI chat page interactions"
```

---

### Task 8: End-to-End Local Verification

**Files:**
- No new files.

- [ ] **Step 1: Add real local config outside git**

Create `apps/api/.env` locally with the real key:

```bash
FASTGPT_API_BASE=http://175.27.228.129:4000/api
FASTGPT_API_KEY=<real-key-from-user>
FASTGPT_CHAT_PATH=/v1/chat/completions
FASTGPT_TIMEOUT_SECONDS=30
WEB_ORIGIN=http://localhost:3000
```

Do not commit `apps/api/.env`.

- [ ] **Step 2: Start API**

Run:

```bash
cd apps/api
uv run uvicorn app.main:app --reload --port 8000
```

Expected: server starts on `http://127.0.0.1:8000`.

- [ ] **Step 3: Start web**

Run in another terminal:

```bash
cd apps/web
npm run dev
```

Expected: server starts on `http://localhost:3000`.

- [ ] **Step 4: Verify chat page manually**

Open `http://localhost:3000/ai`.

Expected:

- Header shows `AI数据`.
- Status chip initially shows `已连接`.
- First prompt chip is `今日推荐`.
- Clicking `今日推荐` sends the message.
- AI answer appears incrementally.
- Stop button aborts an in-progress answer and preserves generated text.
- Network tab shows browser requests `http://localhost:8000/api/ai/chat`, not FastGPT directly.

- [ ] **Step 5: Verify key is not in frontend build**

Run:

```bash
cd apps/web
npm run build
rg "fastgpt|FASTGPT|175.27.228.129|fastgpt-oY6aB3Kxwl5D6Ml5BKuB1SQ4WWbQlDQZG02nmzwuKvFjyqwx6GDhkmXuH" .next || true
```

Expected:

- The API key is not found.
- The FastGPT upstream URL is not found in `.next`.

- [ ] **Step 6: Run full verification**

Run:

```bash
cd apps/api && uv run pytest -q
cd ../web && npm test && npm run build
```

Expected: all commands pass.

- [ ] **Step 7: Commit final verification fixes**

If verification required code changes:

```bash
git add apps/api apps/web
git commit -m "fix: polish AI chat verification issues"
```

If verification required no code changes, do not create an empty commit.

---

## Plan Self-Review

Spec coverage:

- `AI数据` Tab full-screen chat page: Task 6.
- White/gray current product style: Task 6 CSS.
- Welcome state and 3 recommendation questions: Task 6 and Task 7.
- `今日推荐` first: Task 6 and Task 7.
- Bottom fixed input and send: Task 6.
- Backend `/api/ai/chat` proxy: Task 3.
- API base/key in backend config only: Task 1 and Task 8.
- Streaming answer: Task 2, Task 3, Task 5, Task 6.
- Stop generation: Task 6 and Task 8.
- User-readable errors: Task 3, Task 5, Task 6.
- No dashboard/crawler/odds features: scope check and file structure exclude them.

Placeholder scan:

- No `TBD`, `TODO`, or incomplete sections.
- Every code-changing step includes concrete file content or exact snippets.
- Every test step includes exact commands and expected results.

Type consistency:

- Backend request model uses `messages: ChatMessage[]`.
- Frontend stream client sends `{ messages }`.
- SSE events are consistently `chunk`, `done`, and `error`.
- Frontend message roles are limited to `user`, `assistant`, and `system` for payload compatibility.
