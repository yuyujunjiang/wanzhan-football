export type ChatRole = "user" | "assistant" | "system";

export type ChatMessagePayload = {
  role: ChatRole;
  content: string;
};

export type ParsedSseEvent = {
  event: string;
  data: Record<string, unknown>;
};

import { API_BASE_URL } from "./api";

const STREAM_ERROR_MESSAGE = "回答中断，可重试";

/** Same-origin `/api/ai/chat` via Next rewrites (or Nginx in prod); avoids CORS "Failed to fetch". */
function resolveChatUrl(): string {
  const base = API_BASE_URL.replace(/\/$/, "");
  if (base) {
    return `${base}/api/ai/chat`;
  }
  return "/api/ai/chat";
}

function isAbortError(error: unknown): boolean {
  return (
    typeof error === "object" &&
    error !== null &&
    "name" in error &&
    error.name === "AbortError"
  );
}

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
  try {
    const response = await fetch(resolveChatUrl(), {
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

    const processBlock = (block: string) => {
      if (!block.trim()) return;
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
            : STREAM_ERROR_MESSAGE
        );
      }
    };

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";

      for (const block of blocks) {
        processBlock(block);
      }
    }

    buffer += decoder.decode();
    processBlock(buffer);
  } catch (error) {
    if (isAbortError(error)) {
      return;
    }
    params.onError(STREAM_ERROR_MESSAGE);
  }
}
