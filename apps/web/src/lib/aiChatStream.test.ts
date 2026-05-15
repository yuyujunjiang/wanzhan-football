import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { parseSseBlock, streamAiChat } from "./aiChatStream";

const encoder = new TextEncoder();

function createStream(chunks: string[]): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    }
  });
}

function createParams() {
  return {
    messages: [{ role: "user" as const, content: "你好" }],
    signal: new AbortController().signal,
    onChunk: vi.fn(),
    onDone: vi.fn(),
    onError: vi.fn()
  };
}

function mockFetch(response: Response | Promise<Response>) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
}

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

describe("streamAiChat", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("streams multiple SSE blocks", async () => {
    mockFetch(
      new Response(
        createStream([
          'event: chunk\ndata: {"content":"你"}\n\n',
          'event: chunk\ndata: {"content":"好"}\n\n',
          "event: done\ndata: {}\n\n"
        ])
      )
    );
    const params = createParams();

    await streamAiChat(params);

    expect(params.onChunk).toHaveBeenNthCalledWith(1, "你");
    expect(params.onChunk).toHaveBeenNthCalledWith(2, "好");
    expect(params.onDone).toHaveBeenCalledOnce();
    expect(params.onError).not.toHaveBeenCalled();
  });

  it("handles an SSE block split across reads", async () => {
    mockFetch(
      new Response(
        createStream([
          'event: chunk\ndata: {"content":"你',
          '好"}\n\n',
          "event: done\ndata: {}\n\n"
        ])
      )
    );
    const params = createParams();

    await streamAiChat(params);

    expect(params.onChunk).toHaveBeenCalledWith("你好");
    expect(params.onDone).toHaveBeenCalledOnce();
    expect(params.onError).not.toHaveBeenCalled();
  });

  it("passes backend error events to onError", async () => {
    mockFetch(
      new Response(
        createStream(['event: error\ndata: {"message":"AI 服务未配置"}\n\n'])
      )
    );
    const params = createParams();

    await streamAiChat(params);

    expect(params.onError).toHaveBeenCalledWith("AI 服务未配置");
    expect(params.onChunk).not.toHaveBeenCalled();
    expect(params.onDone).not.toHaveBeenCalled();
  });

  it("calls onError for non-OK responses", async () => {
    mockFetch(new Response(null, { status: 503 }));
    const params = createParams();

    await streamAiChat(params);

    expect(params.onError).toHaveBeenCalledWith("AI 服务暂时不可用，请稍后重试");
  });

  it("calls onError when fetch fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));
    const params = createParams();

    await streamAiChat(params);

    expect(params.onError).toHaveBeenCalledWith("回答中断，可重试");
  });

  it("calls onError when stream reading fails", async () => {
    mockFetch(
      new Response(
        new ReadableStream({
          start(controller) {
            controller.error(new Error("read failed"));
          }
        })
      )
    );
    const params = createParams();

    await streamAiChat(params);

    expect(params.onError).toHaveBeenCalledWith("回答中断，可重试");
  });

  it("calls onError for malformed SSE JSON", async () => {
    mockFetch(new Response(createStream(["event: chunk\ndata: {bad json}\n\n"])));
    const params = createParams();

    await streamAiChat(params);

    expect(params.onError).toHaveBeenCalledWith("回答中断，可重试");
  });

  it("processes the final buffered block without a trailing blank line", async () => {
    mockFetch(
      new Response(
        createStream([
          'event: chunk\ndata: {"content":"你好"}\n\n',
          "event: done\ndata: {}"
        ])
      )
    );
    const params = createParams();

    await streamAiChat(params);

    expect(params.onChunk).toHaveBeenCalledWith("你好");
    expect(params.onDone).toHaveBeenCalledOnce();
    expect(params.onError).not.toHaveBeenCalled();
  });

  it("does not call onError when aborted", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new DOMException("Stopped", "AbortError"))
    );
    const params = createParams();

    await streamAiChat(params);

    expect(params.onError).not.toHaveBeenCalled();
  });
});
