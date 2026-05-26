import React from "react";
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

vi.mock("../../lib/matchDayCache", () => ({
  TODAY_RECOMMEND_LABEL: "今日推荐",
  fetchMatchDayCache: vi.fn(async () => ({
    date: "2026-05-19",
    fixed: [{ matchId: 2039843, league: "英超" }],
    dynamic: { byMatchId: {} },
    meta: { createdAt: "x", updatedAt: "x" }
  })),
  buildTodayRecommendApiContent: vi.fn(
    (cache: { date: string }) => `今日推荐${JSON.stringify(cache)}`
  )
}));

describe("ChatPage", () => {
  it("shows prompt chips with 今日推荐 first", () => {
    render(<ChatPage />);

    const buttons = screen.getAllByRole("button");
    expect(buttons[0]).toHaveTextContent("今日推荐");
  });

  it("sends a prompt and appends streamed answer", async () => {
    const user = userEvent.setup();
    const { streamAiChat } = await import("../../lib/aiChatStream");
    render(<ChatPage embedded />);

    await user.click(screen.getByRole("button", { name: "今日推荐" }));

    expect(await screen.findByText("今日推荐")).toBeInTheDocument();
    expect(await screen.findByText("流式回答")).toBeInTheDocument();

    const { fetchMatchDayCache } = await import("../../lib/matchDayCache");
    expect(fetchMatchDayCache).toHaveBeenCalled();
    const call = vi.mocked(streamAiChat).mock.calls.at(-1)?.[0];
    expect(call?.messages[0]).toMatchObject({
      role: "user",
      content: expect.stringMatching(/^今日推荐\{"date":"2026-05-19"/)
    });
  });

  it("renders assistant markdown replies in embedded mode", async () => {
    const { streamAiChat } = await import("../../lib/aiChatStream");
    vi.mocked(streamAiChat).mockImplementationOnce(async ({ onChunk, onDone }) => {
      onChunk("## 今日推荐\n\n- 第一场");
      onDone();
    });

    const user = userEvent.setup();
    render(<ChatPage embedded />);
    await user.click(screen.getByRole("button", { name: "今日推荐" }));

    expect(
      await screen.findByRole("heading", { level: 2, name: "今日推荐" })
    ).toBeInTheDocument();
    expect(screen.getByText("第一场")).toBeInTheDocument();
  });

  it("does not send blank input", async () => {
    render(<ChatPage />);

    expect(screen.getByRole("button", { name: "发送" })).toBeDisabled();
  });
});
